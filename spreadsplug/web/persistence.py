import json
import logging
import sqlite3
from collections import namedtuple

from flask import g
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

);
"""

WORKFLOW_INSTANCES = dict()

DbWorkflow = namedtuple('DbWorkflow', ['id', 'name', 'step', 'step_done',
                                       'capture_start', 'config'])
logger = logging.getLogger('spreadsplug.web.database')


def initialize_database():
    db_path = app.config['database']
    with sqlite3.connect(unicode(db_path)) as con:
        con.executescript(SCHEMA)


def open_connection():
    db_path = Path(app.config['database'])
    if not db_path.exists():
        logger.info('Initializing database.')
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
    config_data = json.dumps(config.flatten())
    with open_connection() as con:
        con.execute("UPDATE WORKFLOW SET config=:config WHERE id=:id",
                    dict(config=config_data, id=id))


def get_workflow(workflow_id):
    if workflow_id in WORKFLOW_INSTANCES:
        return WORKFLOW_INSTANCES[workflow_id]
    logger.debug("Trying to get workflow with id {0} from database"
                 .format(workflow_id))
    with open_connection() as con:
        db_data = con.execute("SELECT * FROM workflow WHERE workflow.id=?",
                              (workflow_id,)).fetchone()
    if db_data is None:
        return None
    logger.debug("Workflow was found:\n{0}".format(db_data))

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
    WORKFLOW_INSTANCES[workflow_id] = workflow
    return workflow


def get_workflow_list():
    with open_connection() as con:
        result = con.execute(
            "SELECT id, name, step, step_done FROM workflow").fetchall()
    return [dict(id=x[0], name=x[1], step=x[2], step_done=bool(x[3]))
            for x in result]
