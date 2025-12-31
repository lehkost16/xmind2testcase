import os
import re
import arrow
import sqlite3
import shutil
from fastapi import UploadFile
from werkzeug.utils import secure_filename
from app.core.config import settings

def allowed_file(filename: str) -> bool:
    """Check if file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in settings.ALLOWED_EXTENSIONS

def check_file_name(name: str) -> str:
    """Sanitize and validate filename."""
    secured = secure_filename(name)
    if not secured:
        secured = re.sub(r'[^\w\d]+', '_', name)
        assert secured, f'Unable to parse file name: {name}!'
    return secured + '.xmind'

import json
from app.services import xmind_service

def save_file(file: UploadFile, db: sqlite3.Connection, project_id: int = None, case_type: str = "功能用例", apply_phase: str = "功能测试阶段"):
    """Save uploaded file and create record."""
    if not file.filename:
        return None, "Please select a file!"
    
    if not allowed_file(file.filename):
        return None, "Invalid file type!"

    filename = file.filename
    upload_to = os.path.join(settings.UPLOAD_FOLDER, filename)

    if os.path.exists(upload_to):
        filename = '{}_{}.xmind'.format(filename[:-6], arrow.now().strftime('%Y%m%d_%H%M%S'))
        upload_to = os.path.join(settings.UPLOAD_FOLDER, filename)

    with open(upload_to, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Parse XMind and get content
    try:
        testcases = xmind_service.get_testcases(filename)
        content_json = json.dumps(testcases)
    except Exception as e:
        print(f"Error parsing xmind: {e}")
        content_json = "[]"

    insert_record(db, filename, project_id=project_id, content=content_json, case_type=case_type, apply_phase=apply_phase)
    return filename, None

def insert_record(db: sqlite3.Connection, xmind_name, note='', project_id=None, content='', case_type="功能用例", apply_phase="功能测试阶段"):
    """Insert upload record into database."""
    c = db.cursor()
    now = str(arrow.now())
    sql = "INSERT INTO records (name, create_on, note, project_id, content, case_type, apply_phase) VALUES (?, ?, ?, ?, ?, ?, ?)"
    c.execute(sql, (xmind_name, now, str(note), project_id, content, case_type, apply_phase))
    db.commit()

def delete_record(filename: str, record_id: int, db: sqlite3.Connection):
    """Delete file and soft-delete record."""
    xmind_file = os.path.join(settings.UPLOAD_FOLDER, filename)
    
    # We might not want to delete the file immediately if we want to keep history?
    # But sticking to original logic for now, just soft delete the record is safer if we want to restore.
    # The original logic deleted files. Let's keep deleting files to prevent clutter?
    # Actually, with multiple records potentially referencing same content if we change logic,
    # but here each upload is a new file.
    
    testlink_file = os.path.join(settings.UPLOAD_FOLDER, filename[:-5] + 'xml')
    zentao_file = os.path.join(settings.UPLOAD_FOLDER, filename[:-5] + 'csv')

    for f in [xmind_file, testlink_file, zentao_file]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except OSError:
                pass

    c = db.cursor()
    sql = 'UPDATE records SET is_deleted=1 WHERE id = ?'
    c.execute(sql, (record_id,))
    db.commit()

def delete_records_keep_latest(db: sqlite3.Connection, keep=20):
    """Clean up old records and files."""
    # This logic might need to be smarter with projects, but keeping it simple for now.
    sql = "SELECT * from records where is_deleted<>1 ORDER BY id desc LIMIT -1 offset {}".format(keep)
    c = db.cursor()
    c.execute(sql)
    rows = c.fetchall()
    for row in rows:
        name = row[2] # Name is 3rd column now? No, let's use name column index based on schema or dict
        # Schema: id, project_id, name, content, create_on, note, is_deleted
        # Indices: 0, 1, 2, 3, 4, 5, 6
        record_id = row[0]
        # name is row[2]
        delete_record(name, record_id, db)

def get_records(db: sqlite3.Connection, limit=8, project_id=None):
    """Fetch recent records with project info."""
    short_name_length = 120
    c = db.cursor()
    
    # Left join with projects to get project name
    if project_id:
        sql = """
            SELECT r.id, r.name, r.create_on, r.note, p.name as project_name, r.project_id, r.case_type, r.apply_phase
            FROM records r 
            LEFT JOIN projects p ON r.project_id = p.id
            WHERE r.is_deleted<>1 AND r.project_id = ?
            ORDER BY r.id DESC 
        """
        c.execute(sql, (project_id,))
    else:
        sql = """
            SELECT r.id, r.name, r.create_on, r.note, p.name as project_name, r.project_id, r.case_type, r.apply_phase
            FROM records r 
            LEFT JOIN projects p ON r.project_id = p.id
            WHERE r.is_deleted<>1 
            ORDER BY r.id DESC 
            LIMIT ?
        """
        c.execute(sql, (limit,))
        
    rows = c.fetchall()

    records = []
    for row in rows:
        record_id, name, create_on, note, project_name, r_project_id, case_type, apply_phase = row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]
        if len(name) > short_name_length:
            short_name = name[:short_name_length] + '...'
        else:
            short_name = name
            
        create_on = arrow.get(create_on).humanize()
        if not project_name:
            project_name = "No Project"
            
        records.append({
            "id": record_id,
            "name": name,
            "short_name": short_name,
            "create_on": create_on,
            "note": note,
            "project_name": project_name,
            "project_id": r_project_id,
            "case_type": case_type,
            "apply_phase": apply_phase
        })
    return records

def get_record_by_filename(db: sqlite3.Connection, filename: str):
    """Get a record by filename."""
    c = db.cursor()
    # Ordered by ID desc to get the latest if duplicates exist (though save_file ensures uniqueness usually)
    sql = "SELECT id, name, content, note, project_id, case_type, apply_phase FROM records WHERE name = ? AND is_deleted <> 1 ORDER BY id DESC LIMIT 1"
    c.execute(sql, (filename,))
    row = c.fetchone()
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "content": row[2],
            "note": row[3],
            "project_id": row[4],
            "case_type": row[5],
            "apply_phase": row[6]
        }
    return None
