from __future__ import unicode_literals

import argparse
import codecs
import datetime
import hashlib
import logging
import multiprocessing
import os
import shutil
import sys
import tempfile
from collections import MutableMapping
from itertools import chain
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
try:
    import colorama
except ImportError:
    colorama = None

if sys.version_info < (3,):
    str = unicode
PY26 = sys.version_info < (2, 7)

BAGIT_VERSION = "0.97"
TAG_INDENT = " "*4
SOFTWARE_AGENT = "bagit.py <http://github.com/libraryofcongress/bagit-python>"
HASH_ALGORITHMS = {
    'md5': hashlib.md5,
    'sha1': hashlib.sha1,
    'sha256': hashlib.sha256,
}
BAGINFO_TAGS = {
    'Source-Organization': "Organization transferring the content.",
    'Organization-Address': "Mailing address of the organization.",
    'Contact-Name': ("Person at the source organization who is responsible"
                     " for the content transfer."),
    'Contact-Phone': ("International format telephone number of person or"
                      " position responsible."),
    'Contact-Email': ("Fully qualified email address of person or position"
                      " responsible."),
    'External-Description': ("A brief explanation of the contents and"
                             " provenance."),
    'External-Identifier': "A sender-supplied identifier for the bag.",
    'Bag-Group-Identifier': ("A sender-supplied identifier for the set, if"
                             " any, of bags to which it logically belongs."),
    'Bag-Count': ("Two numbers separated by \"of\", in particular, \"N of T\","
                  " where T is the total number of bags in a group of bags and"
                  " N is the ordinal number within the group; if T is not"
                  " known, specify it as \"?\" (question mark)."),
    'Internal-Sender-Identifier': ("An alternate sender-specific identifier"
                                   " for the content and/or bag."),
    'Internal-Sender-Description': ("A sender-local prose description of the"
                                    " contents of the bag."),
    'BagIt-Profile-Identifier': ("An URI to a JSON file containing a BagIt"
                                 " profile"),
}

logger = logging.getLogger('bagit')


def iterdir(fpath):
    for root, dirs, files in os.walk(fpath):
        for name in sorted(files):
            yield os.path.join(root, name)


def hash_file(fpath, algorithms):
    digests = {}
    for alg in algorithms:
        try:
            digests[alg] = HASH_ALGORITHMS[alg]()
        except KeyError:
            raise ValidationError("Unknown algorithm: {0}".format(alg))

    with open(fpath, 'rb') as fp:
        total_bytes = 0
        while True:
            data = fp.read(16384)
            total_bytes += len(data)
            if not data:
                break
            for digest in digests.values():
                digest.update(data)
    checksums = dict((alg, digest.hexdigest())
                     for alg, digest in digests.items())
    return fpath, checksums, total_bytes


def hash_file_star(args):
    return hash_file(*args)


class Bag(object):
    def __init__(self, path, bag_info=None, checksums=None,
                 num_processes=None):
        self.path = os.path.abspath(path)
        self._num_processes = num_processes or multiprocessing.cpu_count()
        self._checksum_algs = checksums or []

        if not os.path.exists(self.path):
            os.mkdir(self.path)

        info_fname = self._get_path('bag-info.txt')
        self.info = BagInfo(info_fname, duplicates=True,
                            save_callback=self.add_tagfiles)
        if not self.is_bag(self.path):
            self._init_bag()
        else:
            self._read_bag()
        if bag_info:
            self.info.update(bag_info)
        self.add_tagfiles(info_fname)
        self.fetchfile = None

    @classmethod
    def convert_directory(cls, path, **kwargs):
        tmpdir = tempfile.mkdtemp()
        bag = Bag(tmpdir, **kwargs)
        paths = []
        for fname in os.listdir(path):
            paths.append(os.path.join(path, fname))
        bag.add_payload(*paths)
        shutil.rmtree(path)
        shutil.copytree(tmpdir, path)
        shutil.rmtree(tmpdir)
        bag.path = path
        return bag

    @classmethod
    def from_archive(cls, archpath, target_directory=None):
        if not target_directory:
            target_directory = tempfile.mkdtemp()
        if archpath.endswith('.tar') or archpath[-6:] in ('tar.gz', 'tar.bz2'):
            # TODO: Extract with tarfile
            raise NotImplementedError
        elif archpath.endswith('.zip'):
            # TODO: Extract with zipfile
            raise NotImplementedError
        else:
            raise IOError("Unsupported archive format.")
        return Bag(target_directory)

    @staticmethod
    def is_bag(path):
        return os.path.exists(os.path.join(path, 'bagit.txt'))

    @property
    def payload(self):
        file_iter = chain(*(m.keys() for m in self.manifest_files.values()))
        return sorted(set(self._get_path(f) for f in file_iter))

    @property
    def tagfiles(self):
        file_iter = chain(*(m.keys() for m in self.tagmanifest_files.values()))
        return sorted(set(self._get_path(f) for f in file_iter))

    def add_payload(self, *paths):
        new_num, additional_size = self._add_files(self._get_path('data'),
                                                   self.manifest_files,
                                                   *paths)
        old_length, old_num = map(int, (self.info['Payload-Oxum']
                                        .split('.')))
        self.info['Payload-Oxum'] = "{0}.{1}".format(
            old_length+additional_size, old_num+new_num)

    def remove_payload(self, *paths):
        num_removed = self._remove_files(self._get_path('data'),
                                         self.manifest_files,
                                         *paths)
        old_size, old_num = map(int, self.info['Payload-Oxum'].split('.'))
        new_size = sum(os.stat(f).st_size for f in self.payload)
        self.info['Payload-Oxum'] = "{0}.{1}".format(new_size,
                                                     old_num-num_removed)

    def add_tagfiles(self, *paths):
        any_in_payload = any(os.path.relpath(p, self.path).startswith('data')
                             for p in paths)
        if any_in_payload:
            raise ValueError("One or more of the files are inside of the "
                             "payload directory, this is not permitted for "
                             "tag files.")
        self._add_files(self.path, self.tagmanifest_files, *paths)

    def remove_tagfiles(self, *paths):
        any_in_payload = any(os.path.relpath(p, self.path).startswith('data')
                             for p in paths)
        if any_in_payload:
            raise ValueError("One or more of the files are inside of the "
                             "payload directory, this is not permitted for "
                             "tag files.")
        self._remove_files(self.path, self.tagmanifest_files, *paths)

    def update_payload(self, fast=False):
        try:
            self.validate(fast)
        except ValidationError as exc:
            new_paths = [self._get_path(e.path) for e in exc.details
                         if isinstance(e, UnexpectedFile)
                         and e.path.startswith('data')]
            removed_paths = [self._get_path(e.path) for e in exc.details
                             if isinstance(e, FileMissing)
                             and e.path.startswith('data')]
            if not fast:
                changed_paths = [self._get_path(e.path) for e in exc.details
                                 if isinstance(e, ChecksumMismatch)
                                 and e.path.startswith('data')]
                self.add_payload(*changed_paths)
            self.add_payload(*new_paths)
            self.remove_payload(*removed_paths)

    def validate(self, fast=False):
        BagValidator(self).validate(fast)

    def is_valid(self, fast=False):
        try:
            self.validate(fast)
            return True
        except ValidationError:
            return False

    def check_complete(self):
        BagValidator(self).check_completeness()

    def is_complete(self):
        try:
            self.check_complete()
            return True
        except ValidationError:
            return False

    def check_incomplete(self):
        BagValidator(self).check_incompleteness()

    def is_incomplete(self):
        try:
            self.check_incomplete()
            return True
        except BagError:
            return False

    def fetch(self, parallel_downloads=1):
        # TODO: Implement
        raise NotImplementedError

    def package_as_tar(self, tarpath, fetch_mapping={}, compression='gz'):
        BagPackager(self).make_tar(tarpath, compression)

    def package_as_zip(self, zippath, fetch_mapping={}, compression='gz'):
        BagPackager(self).make_zip(zippath, compression)

    def package_as_zipstream(self, fetch_mapping={}, compression='gz'):
        return BagPackager(self).make_zipstream(compression)

    def _init_bag(self):
        if not self._checksum_algs:
            self._checksum_algs.append('md5')
        if os.listdir(self.path):
            raise BagError("Bag directory not empty!")
        with open(self._get_path('bagit.txt'), "wb") as fp:
            fp.write(("BagIt-Version: {0}\n"
                      "Tag-File-Character-Encoding: UTF-8\n"
                      .format(BAGIT_VERSION)).encode('utf8'))
        self.version = BAGIT_VERSION
        self.manifest_files = dict(
            (alg, Manifest(self._get_path('manifest-{0}.txt'.format(alg))))
            for alg in self._checksum_algs)
        self.tagmanifest_files = dict(
            (alg, Manifest(self._get_path('tagmanifest-{0}.txt'.format(alg))))
            for alg in self._checksum_algs)
        self.info['Bagging-Date'] = datetime.date.strftime(
            datetime.date.today(), "%Y-%m-%d")
        self.info['Bag-Software-Agent'] = SOFTWARE_AGENT
        self.info['Payload-Oxum'] = "0.0"
        os.mkdir(self._get_path('data'))

    def _read_bag(self):
        version = BagInfo(self._get_path('bagit.txt'))['BagIt-Version']
        if version != BAGIT_VERSION:
            raise BagError("BagIt version {0} is not supported, bag needs"
                           " to comply with version {1} of the"
                           " specification")
        self.manifest_files = {}
        for alg in HASH_ALGORITHMS:
            fpath = self._get_path("manifest-{0}.txt".format(alg))
            if os.path.exists(fpath):
                self._checksum_algs.append(alg)
                self.manifest_files[alg] = Manifest(fpath)
        self.tagmanifest_files = {}
        for alg in self._checksum_algs:
            fpath = self._get_path("tagmanifest-{0}.txt".format(alg))
            self.tagmanifest_files[alg] = Manifest(fpath)
        if 'Payload-Oxum' not in self.info:
            self.info['Payload-Oxum'] = "0.0"

    def _get_path(self, fname):
        return os.path.join(self.path, fname)

    def _get_relative_path(self, fname):
        return os.path.relpath(os.path.abspath(fname), self.path)

    def _add_files(self, base_dir, manifests, *paths):
        new_files = []
        for path in paths:
            # ToDO: Verify that the file name is Windows-compatible
            if not os.path.exists(path):
                logger.warning("Path {0} does not exist, will be skipped.")
                continue
            in_bag = os.path.abspath(path).startswith(base_dir)
            is_dir = os.path.isdir(path)
            if is_dir and not os.listdir(path):
                logger.warning(
                    "Path {0} is an empty directory , will be skipped."
                    .format(path))
                continue
            if in_bag:
                if self._get_path(path) in self.payload:
                    logger.debug("Updating payload for {0}")
                else:
                    logger.debug("Adding path {0} to payload".format(path))
            else:
                logger.debug("Copying path {0} to paylod directory".format(path))
                old_path = path
                path = os.path.join(
                    base_dir,
                    (os.path.basename(old_path)
                     or os.path.basename(os.path.dirname(old_path))))
                if is_dir:
                    shutil.copytree(old_path, path)
                else:
                    shutil.copy(old_path, path)
            if is_dir:
                new_files.extend([f for f in iterdir(path)])
            else:
                new_files.append(path)
        if not new_files:
            return 0, 0
        elif len(new_files) > 1:
            pool = multiprocessing.Pool(processes=self._num_processes)
            results = pool.map(
                hash_file_star, ((x, self._checksum_algs) for x in new_files))
            pool.close()
            pool.join()
        else:
            results = [hash_file(new_files[0], self._checksum_algs)]
        additional_size, new_num = 0, 0
        for fpath, checksums, size in results:
            for alg, digest in checksums.items():
                manifests[alg][self._get_relative_path(fpath)] = digest
            additional_size += size
            new_num += 1
        return new_num, additional_size

    def _remove_files(self, base_dir, manifests, *paths):
        num_removed = 0
        for path in paths:
            if not path.startswith(base_dir):
                logger.warn("{0} is not inside base directory, skipping."
                            .format(path))
                continue
            is_dir = os.path.isdir(path)
            if os.path.exists(path):
                if is_dir:
                    shutil.rmtree(path)
                else:
                    os.unlink(path)
                    if path not in self.payload:
                        logger.warn("File {0} not found in payload!"
                                    .format(path))
                        continue
            relpath = self._get_relative_path(path)
            if is_dir:
                for manifest in manifests.values():
                    for fname in manifest:
                        if fname.startswith(relpath):
                            del manifest[fname]
                            num_removed += 1
            else:
                for manifest in manifests.values():
                    if relpath in manifest:
                        del manifest[relpath]
                        num_removed += 1
        return num_removed


class BagValidator(object):
    def __init__(self, bag):
        self._bag = bag

    def validate(self, fast=False):
        self._validate_structure()
        self._validate_contents(fast)
        self._validate_bagittxt()

    def check_completeness(self):
        self._validate_structure()
        self._validate_contents(fast=True, check_oxum=False)
        self._validate_bagittxt()
        return True

    def check_incompleteness(self):
        self._validate_structure()
        self._validate_bagittxt()
        try:
            self._validate_contents(fast=True, check_oxum=False)
        except ValidationError:
            if not os.path.exists(self._bag._get_path('fetch.txt')):
                raise BagError("'fetch.txt' is missing.")
            return True
        return False

    def _validate_structure(self):
        """Checks the structure of the bag, determining if it conforms to the
           BagIt spec. Returns true on success, otherwise it will raise
           a BagValidationError exception.
        """
        if not os.path.isdir(self._bag._get_path('data')):
            raise ValidationError("Missing data directory")
        if not self._bag.manifest_files:
            raise ValidationError("Missing manifest file")
        if not os.path.exists(self._bag._get_path('bagit.txt')):
            raise ValidationError("Missing bagit.txt")

    def _validate_contents(self, fast=False, check_oxum=True):
        #import ipdb; ipdb.set_trace()
        errors = []
        if self._bag.tagfiles:
            errors.extend(self._validate_files(self._bag.path,
                                               self._bag.tagfiles,
                                               self._bag.tagmanifest_files,
                                               check_extra=False, fast=fast))
        if fast and check_oxum and 'Payload-Oxum' not in self._bag.info:
            raise ValidationError("Cannot validate Bag with fast=True if"
                                  " Bag lacks a Payload-Oxum")
        errors.extend(self._validate_files(self._bag._get_path('data'),
                                           self._bag.payload,
                                           self._bag.manifest_files,
                                           fast=fast))
        if check_oxum:
            try:
                self._validate_oxum()
            except ValidationError as e:
                errors.append(e)
        if errors:
            raise ValidationError(errors=errors)

    def _validate_oxum(self):
        oxum = self._bag.info.get('Payload-Oxum')
        if oxum is None:
            return

        # If multiple Payload-Oxum tags (bad idea)
        # use the first listed in bag-info.txt
        if isinstance(oxum, list):
            oxum = oxum[0]

        byte_count, file_count = oxum.split('.', 1)

        if not byte_count.isdigit() or not file_count.isdigit():
            raise ValidationError("Invalid Payload-Oxum: {0}".format(oxum))

        byte_count = int(byte_count)
        file_count = int(file_count)
        total_bytes = 0
        total_files = 0

        for fpath in self._bag.payload:
            if not os.path.exists(fpath):
                logger.warn("File not found: {0}".format(fpath))
                continue
            total_bytes += os.stat(fpath).st_size
            total_files += 1

        if file_count != total_files or byte_count != total_bytes:
            raise ValidationError("Oxum error. Found {0} files and {1} bytes "
                                  "on disk; expected {2} files and {3} bytes."
                                  .format(total_files, total_bytes, file_count,
                                          byte_count))

    def _validate_files(self, base_dir, filelist, manifests, check_extra=True,
                        fast=False):
        errors = []
        # First we'll make sure there's no mismatch between the filesystem
        # and the list of files in the manifest(s)
        if check_extra:
            for fpath in iterdir(base_dir):
                if fpath not in filelist:
                    e = UnexpectedFile(self._bag._get_relative_path(fpath))
                    logger.warn(e)
                    errors.append(e)

        removed_files = []
        for fpath in filelist:
            if not os.path.exists(fpath):
                e = FileMissing(self._bag._get_relative_path(fpath))
                logger.warn(e)
                errors.append(e)
                removed_files.append(fpath)
        filelist = set(filelist) - set(removed_files)
        if not fast and filelist:
            pool = multiprocessing.Pool(self._bag._num_processes)
            results = pool.map(hash_file_star,
                               ((fpath, self._bag._checksum_algs)
                                for fpath in filelist))
            pool.close()
            pool.join()
            for fpath, checksums, _ in results:
                for alg, computed_hash in checksums.items():
                    relpath = self._bag._get_relative_path(fpath)
                    expected = manifests[alg][relpath]
                    if expected != computed_hash:
                        e = ChecksumMismatch(
                            self._bag._get_relative_path(fpath), alg, expected,
                            computed_hash)
                        logger.warn(e)
                        errors.append(e)
        return errors

    def _validate_bagittxt(self):
        """
        Verify that bagit.txt conforms to specification
        """
        with open(self._bag._get_path('bagit.txt'), 'rb') as fp:
            first_line = fp.readline()
            if first_line.startswith(codecs.BOM_UTF8):
                raise ValidationError("bagit.txt must not contain a "
                                      "byte-order mark")


class BagPackager(object):
    def __init__(self, bag, fetch_mapping={}):
        self._bag = bag
        self._fetch_mapping = fetch_mapping

    def _write_bag_to_zipfile(self, zfile):
        if self._fetch_mapping:
            fetchtxt_path = tempfile.mkstemp()[1]
            fetchfile = FetchFile(fetchtxt_path)
        for fpath in iterdir(self._bag.path):
            relpath = self._bag._get_relative_path(fpath)
            if relpath in self._fetch_mapping:
                fetchfile[relpath] = fetchfile[fpath]
            else:
                extract_path = os.path.join(
                    '/', os.path.basename(self._bag.path),
                    self._bag._get_relative_path(fpath)
                )
                zfile.write(str(fpath), extract_path)

    def make_zip(self, zip_path, compression='gz'):
        import zipfile
        compression = zipfile.ZIP_STORED
        if compression == 'gz':
            compression = zipfile.ZIP_DEFLATED
        with zipfile.ZipFile(str(zip_path), 'w', compression) as zfile:
            self._write_bag_to_zipfile(zfile)

    def make_zipstream(self, compression='gz'):
        import zipstream
        compression = zipstream.ZIP_STORED
        if compression == 'gz':
            compression = zipstream.ZIP_DEFLATE
        zstream = zipstream.ZipFile(mode='w', compression=compression)
        self._write_bag_to_zipfile(zstream)
        return zstream

    def make_tar(self, tar_path, compression='gz'):
        import tarfile
        if compression not in (None, 'gz', 'bz2'):
            raise ValueError("compression must be one of (None, 'gz', 'bz2')!")
        if compression is None:
            compression = ''
        mode = 'w{0}'.format(':' + compression if compression else '')
        with tarfile.open(tar_path, mode) as tf:
            if PY26:
                tf.add(self._bag.path, os.path.basename(self._bag.path),
                       recursive=True,
                       exclude=lambda x: x in self._fetch_mapping)
            else:
                tf.add(self._bag.path, os.path.basename(self._bag.path),
                       recursive=True,
                       filter=lambda x: (x if not x.path in self._fetch_mapping
                                         else None))


class BagError(Exception):
    pass


class ValidationError(BagError):
    def __init__(self, message="", errors=[]):
        self.message = message
        self.details = errors

    def __str__(self):
        out = self.message
        if self.details:
            if out:
                out += "\n"
            out += "  - {0}".format("\n  - "
                                    .join(str(e) for e in self.details))
        return out

    def __unicode__(self):
        return self.__str__()

    def __repr__(self):
        return self.__str__()


class ManifestErrorDetail(ValidationError):
    def __init__(self, path):
        self.path = path


class ChecksumMismatch(ManifestErrorDetail):
    def __init__(self, path, algorithm=None, expected=None, found=None):
        self.path = path
        self.algorithm = algorithm
        self.expected = expected
        self.found = found

    def __str__(self):
        return (
            "{0} checksum validation failed (alg={1} expected={2} found={3})"
            .format(self.path, self.algorithm, self.expected, self.found))


class FileMissing(ManifestErrorDetail):
    def __str__(self):
        return ("{0} exists in manifest but not found on filesystem"
                .format(self.path))


class UnexpectedFile(ManifestErrorDetail):
    def __str__(self):
        return ("{0} exists on filesystem but is not in manifest"
                .format(self.path))


class BaseInfo(MutableMapping):
    def __init__(self, path, save_callback=None):
        self._path = path
        self._store = OrderedDict()
        self._save_callback = save_callback
        self.read()

    def read(self):
        raise NotImplementedError

    def save(self):
        raise NotImplementedError

    def __getitem__(self, key):
        return self._store[self.__keytransform__(key)]

    def __setitem__(self, key, value):
        self._store[self.__keytransform__(key)] = value
        self.save()
        if self._save_callback:
            self._save_callback(self._path)

    def __delitem__(self, key):
        del self._store[self.__keytransform__(key)]
        self.save()
        if self._save_callback:
            self._save_callback(self._path)

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)

    def __keytransform__(self, key):
        return key


class BagInfo(BaseInfo):
    def __init__(self, path, duplicates=True, save_callback=None):
        self._duplicates = duplicates
        super(BagInfo, self).__init__(path, save_callback)

    def read(self):
        # Line folding is handled by storing values only after we encounter the
        # start of a new tag, or if we pass the EOF.
        def store(key, value):
            key = self.__keytransform__(key)
            existing = key in self._store
            if existing and self._duplicates:
                if isinstance(self._store[key], tuple):
                    self._store[key] = self._store[key] + (value,)
                else:
                    self._store[key] = (self._store[key], value)
            else:
                self._store[key] = value

        if not os.path.exists(self._path):
            return
        key = value = None
        with open(self._path, 'rb') as fp:
            for num, line in enumerate(fp):
                # If byte-order mark ignore it for now.
                if 0 == num:
                    if line.startswith(codecs.BOM_UTF8):
                        line = line.lstrip(codecs.BOM_UTF8)

                line = line.decode("utf8")

                # Skip over any empty or blank lines.
                if len(line) == 0 or line.isspace():
                    continue

                if line[0].isspace():  # folded line
                    value += (" " + line.strip())
                    continue

                # Starting a new tag; yield the last one.
                if key:
                    store(key, value)

                parts = line.strip().split(':', 1)
                key = parts[0].strip()
                value = parts[1].strip()
            store(key, value)

    def save(self):
        with open(self._path, "wb") as fp:
            for key, value in self._store.items():
                if isinstance(value, tuple):
                    for subval in value:
                        fp.write(self._to_file_entry(key, subval)
                                 .encode('utf-8'))
                else:
                    fp.write(self._to_file_entry(key, value).encode('utf-8'))

    def _to_file_entry(self, key, value):
        entry = "{key}: {value}".format(key=key, value=value)
        if len(entry) < 79:
            return entry + "\n"
        elems = entry.split(" ")
        if len(elems) == 2:
            return entry + "\n"
        formatted = ""
        for elem in elems:
            line_length = len(formatted.split("\n")[-1])
            if (line_length + len(elem)) > 78:
                formatted += "\n{indent}{elem}".format(indent=TAG_INDENT,
                                                       elem=elem)
            else:
                if elem != key + ':':
                    formatted += " "
                formatted += "{elem}".format(elem=elem)
        return formatted + "\n"

    def __keytransform__(self, key):
        return "-".join(x.capitalize() for x in key.split("-"))


class Manifest(BaseInfo):
    def read(self):
        if not os.path.exists(self._path):
            with open(self._path, 'w') as fp:
                pass
            return
        with open(self._path, 'rb') as fp:
            for line in fp:
                line = line.strip().decode('utf8')
                if not line or line.startswith("#"):
                    continue
                entry = line.split(None, 1)
                if len(entry) < 2:
                    logger.warn("Invalid entry: {0}".format(entry))
                digest, path = line.split(None, 1)
                path = self._deserialize_fname(
                    os.path.normpath(path).lstrip('*'))
                if path in self._store:
                    logger.warn("Duplicate entry: {0}".format(path))
                self._store[path] = digest

    def save(self):
        with open(self._path, 'wb') as fp:
            for path, digest in self.items():
                fp.write("{0}  {1}\n"
                         .format(digest, self._serialize_fname(path))
                         .encode('utf8'))

    # NOTE: It seems that some applications put newlines or carriage returns
    #       inside of file names, so we escape those here as to not break our
    #       parser. See this issue for more details:
    #       https://github.com/LibraryOfCongress/bagit-python/issues/12
    def _serialize_fname(self, fname):
        return fname.replace("\n", "%0A").replace("\r", "%0D")

    def _deserialize_fname(self, fname):
        return fname.replace("%0A", "\n").replace("%0D", "\r")


class FetchFile(Manifest):
    pass


class ColorStreamHandler(logging.StreamHandler):
    """ A colorized logging StreamHandler.

    Only emits colorized output when the 'colorama' library was successfully
    imported.
    """

    @property
    def is_tty(self):
        """ Check if we are using a "real" TTY. If we are not using a TTY it
        means that the colour output should be disabled.

        :return: Using a TTY status
        :rtype: bool
        """
        try:
            return getattr(self.stream, 'isatty', None)()
        except:
            return False

    def emit(self, record):
        if colorama:
            colors = {
                'DEBUG': colorama.Fore.CYAN,
                'INFO': colorama.Fore.GREEN,
                'WARN': colorama.Fore.YELLOW,
                'WARNING': colorama.Fore.YELLOW,
                'ERROR': colorama.Fore.RED,
                'CRIT': colorama.Back.RED + colorama.Fore.WHITE,
                'CRITICAL': colorama.Back.RED + colorama.Fore.WHITE
            }
        try:
            message = self.format(record)
            if not colorama or not self.is_tty:
                self.stream.write(message)
            else:
                self.stream.write(colors[record.levelname]
                                  + message + colorama.Style.RESET_ALL)
            self.stream.write(getattr(self, 'terminator', '\n'))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


def _parse_args(args):
    class StoreInfo(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            if not hasattr(namespace, 'bag_info'):
                namespace.bag_info = {}
            namespace.bag_info[option_string.strip('--')] = values

    parser = argparse.ArgumentParser(
        prog="bagit",
        description=("Command-Line utility for working with directories"
                     " complying with the BagIt specification"))
    parser.add_argument("path", nargs='+', action='store',
                        help="Paths to BagIt directories")
    parser.add_argument('--processes', action='store', type=int,
                        dest='processes', default=multiprocessing.cpu_count(),
                        help='Number of CPU cores to use for file hashing.')
    parser.add_argument('--log', action='store', dest='log', required=False,
                        help="Path to logfile")
    parser.add_argument('--quiet', action='store_true', dest='quiet',
                        help="Be less verbose")
    parser.add_argument('--validate', action='store_true', dest='validate',
                        help="Validate bags")
    parser.add_argument('--fast', action='store_true', dest='fast',
                        default=False,
                        help=("Skip checksum verification when validating and"
                              " only verify file sizes."))
    for alg in HASH_ALGORITHMS:
        parser.add_argument(
            "--{0}".format(alg), action='append_const', const=alg,
            dest='checksums',
            help="Generate {0} manifest when creating a bag{1}"
                 .format(alg.upper(), ' (default)' if alg == 'md5' else ''))
    for tag, docstr in BAGINFO_TAGS.items():
        parser.add_argument(
            "--{0}".format(tag.lower()), type=str, action=StoreInfo,
            metavar="value", help=docstr)
    return parser.parse_args(args)


def _setup_logging(quiet=False, logfile=None):
    level = logging.ERROR if quiet else logging.INFO
    if logfile:
        logging.basicConfig(filename=logfile, level=level)
    else:
        logging.basicConfig(level=level)


def main(args):
    _setup_logging(quiet=args.quiet, logfile=args.log)
    for path in args.path:
        if args.validate and Bag.is_bag(path):
            # Validate bag
            try:
                bag = Bag(path, num_processes=args.processes)
                bag.validate(fast=args.fast)
                if args.fast:
                    logger.info("{0} is valid according to file sizes."
                                .format(path))
                else:
                    logger.info("{0} is valid.".format(path))
            except ValidationError as e:
                logger.error("{0} is invalid:\n{1}".format(path, e))
        elif args.validate:
            logger.error("{0} is not a bag, cannot be verified.".format(path))
            continue
        elif Bag.is_bag(path) and hasattr(args, 'bag_info'):
            # Add info to existing bag
            bag = Bag(path, bag_info=args.bag_info)
            logger.info("bag-info.txt in {0} updated.".format(path))
        elif Bag.is_bag(path):
            # Path is an existing bag, but no action was selected, so we skip
            # it
            logger.warn("{0} is already a bag, will not be converted."
                        .format(path))
            continue
        else:
            Bag.convert_directory(
                path, num_processes=args.processes,
                bag_info=args.bag_info if hasattr(args, 'bag_info') else None,
                checksums=args.checksums)
            logger.info("{0} converted to bag.".format(path))


if __name__ == '__main__':
    args = _parse_args(sys.argv)
    main(args)
