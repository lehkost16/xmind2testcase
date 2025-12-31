import sqlite3
import json
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import Any, Dict, List
from app.api.deps import get_db
from app.services import file_service

router = APIRouter()

class RecordUpdate(BaseModel):
    name: str = None
    note: str = None
    content: List[Dict[str, Any]] = None # List of suites/cases

@router.put("/{record_id}")
def update_record(record_id: int, update: RecordUpdate, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    
    # Check if record exists
    cursor.execute("SELECT id FROM records WHERE id = ? AND is_deleted = 0", (record_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Record not found")
    
    fields = []
    values = []
    
    if update.name is not None:
        fields.append("name = ?")
        values.append(update.name)
        
    if update.note is not None:
        fields.append("note = ?")
        values.append(update.note)
        
    if update.content is not None:
        fields.append("content = ?")
        values.append(json.dumps(update.content))
        
    if not fields:
         return {"status": "no changes"}
         
    values.append(record_id)
    sql = f"UPDATE records SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(sql, tuple(values))
    db.commit()
    
    return {"status": "success"}

@router.get("/{record_id}/content")
def get_record_content(record_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT content FROM records WHERE id = ? AND is_deleted = 0", (record_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
        
    content = row[0]
    if not content:
        return []
        
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return []

@router.delete("/{record_id}")
async def delete_record(record_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Delete a record and associated files"""
    cursor = db.cursor()
    cursor.execute("SELECT name FROM records WHERE id = ? AND is_deleted = 0", (record_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
        
    filename = row[0]
    file_service.delete_record(filename, record_id, db)
    
    return {"status": "success", "message": f"Record {record_id} deleted"}

@router.get("/{record_id}/export", name="export_record")
def export_record(record_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT name, content FROM records WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    
    name, content = row
    testcases = []
    import json
    try:
        testcases = json.loads(content) if content else []
    except:
        pass
        
    # Stats
    total = len(testcases)
    passed = sum(1 for t in testcases if t.get('result') == 'Pass')
    failed = sum(1 for t in testcases if t.get('result') == 'Fail')
    blocked = sum(1 for t in testcases if t.get('result') == 'Block')
    skipped = sum(1 for t in testcases if t.get('result') == 'Skip')
    executed = passed + failed + blocked
    
    # Generate MD Report
    report = f"""# Test Execution Report: {name}
    
## Summary
- **Total Test Cases**: {total}
- **Executed**: {executed}
- **Pass**: {passed}
- **Fail**: {failed}
- **Block**: {blocked}
- **Skip**: {skipped}

## Details
| Case ID | Suite | Title | Result | Comment |
|---------|-------|-------|--------|---------|
"""
    for idx, test in enumerate(testcases, 1):
        result = test.get('result', 'Not Run')
        comment = test.get('comment', '')
        suite = test.get('suite', 'Root')
        title = test.get('name', '')
        
        # Simple cleanup for table format
        title = title.replace('|', '-').replace('\\n', ' ')
        comment = comment.replace('|', '-').replace('\\n', ' ')
        
        report += f"| {idx} | {suite} | {title} | {result} | {comment} |\n"
        
    from fastapi.responses import Response
    return Response(
        content=report, 
        media_type="text/markdown", 
        headers={"Content-Disposition": f"attachment; filename={name}_report.md"}
    )
