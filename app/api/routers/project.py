import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.api.deps import get_db

router = APIRouter()

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    create_on: str

@router.post("/", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    import datetime
    create_on = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Check duplicate
    cursor.execute("SELECT id FROM projects WHERE name = ? AND is_deleted = 0", (project.name,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Project with this name already exists")

    cursor.execute(
        "INSERT INTO projects (name, description, create_on) VALUES (?, ?, ?)",
        (project.name, project.description, create_on)
    )
    db.commit()
    project_id = cursor.lastrowid
    
    return {
        "id": project_id,
        "name": project.name,
        "description": project.description,
        "create_on": create_on
    }

@router.get("/", response_model=List[ProjectResponse])
def list_projects(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, name, description, create_on FROM projects WHERE is_deleted = 0 ORDER BY id DESC")
    rows = cursor.fetchall()
    return [
        {"id": row[0], "name": row[1], "description": row[2], "create_on": row[3]}
        for row in rows
    ]

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

@router.put("/{project_id}")
def update_project(project_id: int, project: ProjectUpdate, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    
    # Check if name is being changed and if new name already exists elsewhere
    if project.name:
        cursor.execute("SELECT id FROM projects WHERE name = ? AND id != ? AND is_deleted = 0", (project.name, project_id))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Another project with this name already exists")

    fields = []
    values = []
    
    if project.name is not None:
        fields.append("name = ?")
        values.append(project.name)
        
    if project.description is not None:
        fields.append("description = ?")
        values.append(project.description)
        
    if not fields:
        return {"status": "no changes"}
        
    values.append(project_id)
    sql = f"UPDATE projects SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(sql, tuple(values))
    db.commit()
    return {"status": "success"}

@router.delete("/{project_id}")
def delete_project(project_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    
    # Safety Check: 如果项目下还存在测试记录，则不允许删除
    cursor.execute("SELECT COUNT(*) FROM records WHERE project_id = ?", (project_id,))
    record_count = cursor.fetchone()[0]
    
    if record_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"该项目下存在 {record_count} 条测试记录，请先删除或迁移相关记录后再尝试删除项目。"
        )

    # 软删除项目
    cursor.execute("UPDATE projects SET is_deleted = 1 WHERE id = ?", (project_id,))
    db.commit()
    return {"status": "success"}
