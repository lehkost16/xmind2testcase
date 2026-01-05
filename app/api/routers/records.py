import sqlite3
import json
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import Any, Dict, List
from app.api.deps import get_db
from app.services import file_service
from fastapi.responses import Response

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
    try:
        testcases = json.loads(content) if content else []
    except:
        pass
        
    # --- Statistics Calculation ---
    
    # 1. Case Stats
    total_cases = len(testcases)
    case_stats = {'Pass': 0, 'Fail': 0, 'Block': 0, 'Skip': 0, 'Not Run': 0}
    
    # 2. Step Stats
    step_stats = {'Total': 0, 'pass': 0, 'fail': 0, 'not_run': 0}
    
    # 3. Suite Stats
    suite_stats = {} # {suite_name: {total, pass, fail, block, skip, not_run}}

    for test in testcases:
        # Case Stat
        res = test.get('result', 'Not Run')
        # Normalize result key to match our map if needed, but usually it's exact
        if res not in case_stats:
            case_stats['Not Run'] += 1
        else:
            case_stats[res] += 1
            
        # Step Stat
        steps = test.get('steps', [])
        for step in steps:
            step_stats['Total'] += 1
            s_status = step.get('status', 'not_run')
            step_stats[s_status] = step_stats.get(s_status, 0) + 1
            
        # Suite Stat
        suite = test.get('suite', 'Root')
        if suite not in suite_stats:
            suite_stats[suite] = {'Total': 0, 'Pass': 0, 'Fail': 0, 'Block': 0, 'Skip': 0, 'Not Run': 0}
        
        suite_stats[suite]['Total'] += 1
        suite_stats[suite][res] = suite_stats[suite].get(res, 0) + 1

    executed_cases = case_stats['Pass'] + case_stats['Fail'] + case_stats['Block']
    
    # --- Generate Report ---
    report = f"""# {name.split('.')[0]}执行结果

## 1. 模块/套件执行概况
- **总模块数**: {total_cases}
- **已执行**: {executed_cases}
- **通过**: {case_stats['Pass']}
- **失败**: {case_stats['Fail']}
- **阻塞**: {case_stats['Block']}
- **跳过**: {case_stats['Skip']}

## 2. 用例执行概况
- **总用例数**: {step_stats['Total']}
- **通过**: {step_stats['pass']}
- **失败**: {step_stats['fail']}
- **未执行**: {step_stats['not_run']}

## 3. 模块/套件执行详情

| 模块/套件 | 功能模块 | 通过 | 失败 | 阻塞 | 跳过 | 未执行 |
|---|---|---|---|---|---|---|
"""
    
    for suite, stats in suite_stats.items():
        report += f"| {suite} | {stats['Total']} | {stats['Pass']} | {stats['Fail']} | {stats['Block']} | {stats['Skip']} | {stats['Not Run']} |\n"

    report += """
## 4. 详细记录

| Case ID | Suite | 名称 | 结果 | 备注 |  
|---|---|---|---|---|
"""
    result_mapping = {
        'Pass': '通过',
        'Fail': '失败',
        'Block': '阻塞',
        'Skip': '跳过',
        'Not Run': '未执行'
    }

    for idx, test in enumerate(testcases, 1):
        raw_result = test.get('result', 'Not Run')
        result = result_mapping.get(raw_result, raw_result)
        
        # Ensure values are strings to prevent crashes on None
        comment = str(test.get('comment') or '')
        suite = str(test.get('suite') or 'Root')
        title = str(test.get('name') or '')
        
        # Simple cleanup
        title = title.replace('|', '-').replace('\n', ' ')
        comment = comment.replace('|', '-').replace('\n', ' ')
        
        report += f"| {idx} | {suite} | {title} | {result} | {comment} |\n"
        
    encoded_filename = quote(f"{name}_report.md")
    return Response(
        content=report, 
        media_type="text/markdown", 
        headers={"Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"}
    )
