import json
import zipfile
import io
import os

def create_xmind_template(output_path):
    # Modern XMind (ZEN) format content.json structure
    content = [
        {
            "id": "sheet1",
            "class": "sheet",
            "title": "测试用例设计",
            "rootTopic": {
                "id": "root",
                "title": "现代化系统测试模板/",
                "children": {
                    "attached": [
                        {
                            "id": "suite1",
                            "title": "用户权限模块 (TestSuite)",
                            "note": "测试用户登录、登出及权限校验流程",
                            "children": {
                                "attached": [
                                    {
                                        "id": "case1",
                                        "title": "管理员账号正常登录 (TestCase)",
                                        "markers": [{"markerId": "priority-1"}],
                                        "note": "前置条件：账号已激活且拥有管理员权限",
                                        "children": {
                                            "attached": [
                                                {
                                                    "id": "s1",
                                                    "title": "1. 访问登录页并输入管理员凭据",
                                                    "children": {
                                                        "attached": [
                                                            {
                                                                "id": "e1",
                                                                "title": "页面跳转至后台管理面板"
                                                            }
                                                        ]
                                                    }
                                                },
                                                {
                                                    "id": "s2",
                                                    "title": "2. 点击右上角登出按钮",
                                                    "children": {
                                                        "attached": [
                                                            {
                                                                "id": "e2",
                                                                "title": "成功返回登录页，Session 清除"
                                                            }
                                                        ]
                                                    }
                                                }
                                            ]
                                        }
                                    },
                                    {
                                        "id": "case2",
                                        "title": "密码错误登录失败校验",
                                        "markers": [{"markerId": "priority-2"}],
                                        "children": {
                                            "attached": [
                                                {
                                                    "id": "s3",
                                                    "title": "1. 输入正确的用户名和错误的密码",
                                                    "children": {
                                                        "attached": [
                                                            {
                                                                "id": "e3",
                                                                "title": "提示'用户名或密码错误'，保持在登录页"
                                                            }
                                                        ]
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            "id": "suite2",
                            "title": "搜索功能 (TestSuite)",
                            "children": {
                                "attached": [
                                    {
                                        "id": "case3",
                                        "title": "空关键词搜索",
                                        "markers": [{"markerId": "priority-3"}],
                                        "children": {
                                            "attached": [
                                                {
                                                    "id": "s4",
                                                    "title": "1. 在搜索框不输入内容直接点击搜索",
                                                    "children": {
                                                        "attached": [
                                                            {
                                                                "id": "e4",
                                                                "title": "显示全部结果或提示请输入关键词"
                                                            }
                                                        ]
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
    ]

    metadata = {"activeSheetId": "sheet1", "properties": {"title": "XMind测试用例模板"}}
    manifest = {
        "file-entries": {
            "content.json": {"full-path": "content.json"},
            "metadata.json": {"full-path": "metadata.json"}
        }
    }

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as xmind:
        xmind.writestr('content.json', json.dumps(content, ensure_ascii=False))
        xmind.writestr('metadata.json', json.dumps(metadata, ensure_ascii=False))
        xmind.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False))

if __name__ == "__main__":
    target = "/home/nana/PyProjects/xmind2testcase/app/static/guide/XMind测试用例模板.xmind"
    # Backup old one
    if os.path.exists(target):
        os.rename(target, target + ".bak")
    create_xmind_template(target)
    print(f"Template generated at {target}")
