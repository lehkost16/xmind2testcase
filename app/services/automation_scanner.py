import re
import os
import logging
from typing import Set

class AutomationScanner:
    """
    A simple scanner to extract TC_IDs from automation code.
    It looks for @pytest.mark.tc_id("ID") or similar patterns.
    """
    
    def __init__(self):
        # Regex to match @pytest.mark.tc_id("TC-001") or @pytest.mark.tc_id('TC-001')
        self.tc_id_pattern = re.compile(r'@pytest\.mark\.tc_id\([\'"](.+?)[\'"]\)')

    def scan_directory(self, root_path: str) -> Set[str]:
        """
        Scan a directory recursively for Python files and extract TC_IDs.
        """
        found_ids = set()
        
        if not os.path.exists(root_path):
            logging.warning(f"Scanner path does not exist: {root_path}")
            return found_ids

        for root, _, files in os.walk(root_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    found_ids.update(self.scan_file(file_path))
        
        return found_ids

    def scan_file(self, file_path: str) -> Set[str]:
        """
        Extract TC_IDs from a single file.
        """
        ids = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                matches = self.tc_id_pattern.findall(content)
                for m in matches:
                    ids.add(m)
        except Exception as e:
            logging.error(f"Error scanning file {file_path}: {e}")
            
        return ids

# Global instance
scanner = AutomationScanner()
