import json
import logging
import sqlite3
from collections import namedtuple

from spreads.workflow import Workflow
from spreads.vendor.pathlib import Path

from spreadsplug.web import app

SCHEMA = """
CREATE TABLE workflow (
    id              INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    name            TEXT,
    step            TEXT,
    step_done       BOOLEAN,
    capture_start   INTEGER,
    config          TEXT
);

CREATE TABLE queue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    workflow_id     INTEGER,
    FOREIGN KEY (workflow_id) REFERENCES workflow(id)
);
"""

WORKFLOW_INSTANCES = dict()

DbWorkflow = namedtuple('DbWorkflow', ['id', 'name', 'step', 'step_done',
                                       'capture_start', 'config'])
logger = logging.getLogger('spreadsplug.web.database')


def initialize_database():
    logger.info("Initializing database.")
    db_path = app.config['database']
    with sqlite3.connect(unicode(db_path)) as con:
        con.executescript(SCHEMA)


def open_connection():
    db_path = Path(app.config['database'])
    if not db_path.exists():
        initialize_database()
    return sqlite3.connect(unicode(db_path))


def save_workflow(workflow):
    data = DbWorkflow(id=None, name=workflow.path.name,
                      step=workflow.step, step_done=workflow.step_done,
                      capture_start=workflow.capture_start,
                      config=json.dumps(workflow.config.flatten()))
    logger.debug("Writing workflow to database:\n{0}".format(data))
    with open_connection() as con:
        workflow_id = con.execute("INSERT INTO workflow VALUES (?,?,?,?,?,?)",
                                  data).lastrowid
    logger.debug("Workflow written to database with id {0}"
                 .format(workflow_id))
    WORKFLOW_INSTANCES[workflow_id] = workflow
    return workflow_id


def update_workflow_config(id, config):
    logger.debug("Updating configuration for workflow {0}.".format(id))
    config_data = json.dumps(config.flatten())
    with open_connection() as con:
        con.execute("UPDATE WORKFLOW SET config=:config WHERE id=:id",
                    dict(config=config_data, id=id))


def get_workflow(workflow_id):
    # See if the workflow is among our cached instances
    if workflow_id in WORKFLOW_INSTANCES:
        return WORKFLOW_INSTANCES[workflow_id]
    logger.debug("Loading workflow {0} from database".format(workflow_id))
    with open_connection() as con:
        db_data = con.execute("SELECT * FROM workflow WHERE workflow.id=?",
                              (workflow_id,)).fetchone()
    if db_data is None:
        logger.warn("Workflow {0} was not found.".format(workflow_id))
        return None

    db_workflow = DbWorkflow(*db_data)

    # Try to load configuration from database
    if db_workflow.config is not None:
        config = json.loads(db_workflow.config)
    else:
        config = None
    workflow = Workflow(
        path=Path(app.config['base_path'])/db_workflow.name,
        config=config,
        step=db_workflow.step,
        step_done=bool(db_workflow.step_done))
    workflow.capture_start = db_workflow.capture_start
    # NOTE: For convenience, we store the workflow_id directly in the object
    workflow.id = workflow_id
    WORKFLOW_INSTANCES[workflow.id] = workflow
    return workflow


def get_all_workflows():
    if WORKFLOW_INSTANCES:
        return WORKFLOW_INSTANCES
    logger.debug("Obtaining all workflows from database.")
    with open_connection() as con:
        result = con.execute(
            "SELECT id FROM workflow").fetchall()
    return {x[0]: get_workflow(x[0]) for x in result}


def delete_workflow(workflow_id):
    logger.debug("Deleting workflow {0} from database.".format(workflow_id))
    del(WORKFLOW_INSTANCES[workflow_id])
    with open_connection() as con:
        con.execute("DELETE FROM workflow WHERE id = ?", (workflow_id,))


def append_to_queue(workflow_id):
    logger.debug("Adding workflow {0} to job queue.".format(workflow_id))
    with open_connection() as con:
        pos = con.execute("INSERT INTO queue VALUES (?,?)",
                          (None, workflow_id)).lastrowid
    return pos


def delete_from_queue(queue_position):
    logger.debug("Removing job {0} from job queue.".format(queue_position))
    with open_connection() as con:
        con.execute("DELETE FROM queue WHERE id = ?", queue_position)


def pop_from_queue():
    with open_connection() as con:
        result = con.execute(
            "SELECT id, workflow_id FROM queue ORDER BY id LIMIT 1"
        ).fetchone()
        if not result:
            return None
        job_id, workflow_id = result
        logger.debug("Popping workflow {0} from queue.".format(workflow_id))
        con.execute("DELETE FROM queue WHERE id = ?", (job_id, ))
    return get_workflow(workflow_id)


def get_queue():
    logger.debug("Loading job queue from database.")
    with open_connection() as con:
        dbdata = con.execute(
            "SELECT id, workflow_id FROM queue ORDER BY id"
        ).fetchall()
    return {job_id: get_workflow(workflow_id)
            for job_id, workflow_id in dbdata}
