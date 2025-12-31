/**
 * Pagination Component
 * 通用的客户端分页组件,支持表格分页、搜索集成、响应式设计
 */
class Pagination {
    constructor(options = {}) {
        this.tableId = options.tableId; // tbody 的 ID
        this.containerId = options.containerId || `${this.tableId}-pagination`;
        this.itemsPerPage = options.itemsPerPage || 20;
        this.currentPage = 1;
        this.onPageChange = options.onPageChange || null;
        
        this.tbody = document.getElementById(this.tableId);
        if (!this.tbody) {
            console.error(`Table body with id "${this.tableId}" not found`);
            return;
        }
        
        this.allRows = Array.from(this.tbody.getElementsByTagName('tr'));
        this.visibleRows = [...this.allRows]; // 初始化为所有行
        
        this.init();
    }
    
    init() {
        // 创建分页容器
        this.createContainer();
        
        // 初始渲染
        this.render();
        
        // 添加键盘导航
        this.addKeyboardNavigation();
    }
    
    createContainer() {
        // 查找或创建分页容器
        let container = document.getElementById(this.containerId);
        if (!container) {
            container = document.createElement('div');
            container.id = this.containerId;
            container.className = 'pagination-container';
            
            // 插入到表格父元素之后
            const tableParent = this.tbody.closest('table');
            if (tableParent && tableParent.parentNode) {
                tableParent.parentNode.insertBefore(container, tableParent.nextSibling);
            }
        }
        this.container = container;
    }
    
    getTotalPages() {
        return Math.ceil(this.visibleRows.length / this.itemsPerPage);
    }
    
    render() {
        const totalPages = this.getTotalPages();
        const totalItems = this.visibleRows.length;
        
        // 如果只有一页或没有数据,隐藏分页控件
        if (totalPages <= 1) {
            this.container.style.display = 'none';
            this.showPage(1);
            return;
        }
        
        this.container.style.display = 'flex';
        
        // 确保当前页在有效范围内
        if (this.currentPage > totalPages) {
            this.currentPage = totalPages;
        }
        if (this.currentPage < 1) {
            this.currentPage = 1;
        }
        
        const startItem = (this.currentPage - 1) * this.itemsPerPage + 1;
        const endItem = Math.min(this.currentPage * this.itemsPerPage, totalItems);
        
        this.container.innerHTML = `
            <div class="pagination-info">
                显示 <strong>${startItem}-${endItem}</strong> 条，共 <strong>${totalItems}</strong> 条
            </div>
            <div class="pagination-controls">
                <button class="page-btn" onclick="window.paginationInstances['${this.tableId}'].goToPage(1)" 
                        ${this.currentPage === 1 ? 'disabled' : ''} title="首页">
                    ««
                </button>
                <button class="page-btn" onclick="window.paginationInstances['${this.tableId}'].goToPage(${this.currentPage - 1})" 
                        ${this.currentPage === 1 ? 'disabled' : ''} title="上一页">
                    ‹
                </button>
                ${this.renderPageNumbers(totalPages)}
                <button class="page-btn" onclick="window.paginationInstances['${this.tableId}'].goToPage(${this.currentPage + 1})" 
                        ${this.currentPage === totalPages ? 'disabled' : ''} title="下一页">
                    ›
                </button>
                <button class="page-btn" onclick="window.paginationInstances['${this.tableId}'].goToPage(${totalPages})" 
                        ${this.currentPage === totalPages ? 'disabled' : ''} title="末页">
                    »»
                </button>
            </div>
            <div class="pagination-page-size">
                <label>每页</label>
                <select onchange="window.paginationInstances['${this.tableId}'].updatePageSize(this.value)">
                    <option value="10" ${this.itemsPerPage === 10 ? 'selected' : ''}>10</option>
                    <option value="20" ${this.itemsPerPage === 20 ? 'selected' : ''}>20</option>
                    <option value="50" ${this.itemsPerPage === 50 ? 'selected' : ''}>50</option>
                    <option value="100" ${this.itemsPerPage === 100 ? 'selected' : ''}>100</option>
                </select>
                <label>条</label>
            </div>
        `;
        
        this.showPage(this.currentPage);
    }
    
    renderPageNumbers(totalPages) {
        let pages = [];
        const current = this.currentPage;
        const delta = 2; // 当前页左右各显示2页
        
        // 始终显示首页
        if (current > delta + 2) {
            pages.push(this.createPageButton(1));
            if (current > delta + 3) {
                pages.push('<span class="page-ellipsis">...</span>');
            }
        }
        
        // 显示当前页附近的页码
        for (let i = Math.max(1, current - delta); i <= Math.min(totalPages, current + delta); i++) {
            pages.push(this.createPageButton(i));
        }
        
        // 始终显示末页
        if (current < totalPages - delta - 1) {
            if (current < totalPages - delta - 2) {
                pages.push('<span class="page-ellipsis">...</span>');
            }
            pages.push(this.createPageButton(totalPages));
        }
        
        return pages.join('');
    }
    
    createPageButton(page) {
        const isActive = page === this.currentPage;
        return `<button class="page-btn ${isActive ? 'active' : ''}" 
                        onclick="window.paginationInstances['${this.tableId}'].goToPage(${page})"
                        ${isActive ? 'disabled' : ''}>
                    ${page}
                </button>`;
    }
    
    showPage(page) {
        const start = (page - 1) * this.itemsPerPage;
        const end = start + this.itemsPerPage;
        
        // 隐藏所有行
        this.allRows.forEach(row => {
            row.style.display = 'none';
        });
        
        // 只显示当前页的可见行
        this.visibleRows.slice(start, end).forEach(row => {
            row.style.display = '';
        });
        
        // 触发回调
        if (this.onPageChange) {
            this.onPageChange(page);
        }
    }
    
    goToPage(page) {
        const totalPages = this.getTotalPages();
        if (page < 1 || page > totalPages) return;
        
        this.currentPage = page;
        this.render();
        
        // 滚动到表格顶部
        const table = this.tbody.closest('table');
        if (table) {
            table.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
    
    updatePageSize(size) {
        this.itemsPerPage = parseInt(size);
        this.currentPage = 1; // 重置到第一页
        this.render();
    }
    
    /**
     * 刷新分页 - 在搜索/筛选后调用
     * @param {Array} visibleRows - 可选,传入筛选后的行数组
     */
    refresh(visibleRows = null) {
        if (visibleRows) {
            this.visibleRows = visibleRows;
        } else {
            // 自动检测可见行
            this.visibleRows = this.allRows.filter(row => {
                const display = window.getComputedStyle(row).display;
                return display !== 'none';
            });
        }
        
        this.currentPage = 1; // 重置到第一页
        this.render();
    }
    
    addKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            // 只在没有聚焦输入框时响应
            if (document.activeElement.tagName === 'INPUT' || 
                document.activeElement.tagName === 'TEXTAREA' ||
                document.activeElement.tagName === 'SELECT') {
                return;
            }
            
            const totalPages = this.getTotalPages();
            
            if (e.key === 'ArrowLeft' && this.currentPage > 1) {
                e.preventDefault();
                this.goToPage(this.currentPage - 1);
            } else if (e.key === 'ArrowRight' && this.currentPage < totalPages) {
                e.preventDefault();
                this.goToPage(this.currentPage + 1);
            }
        });
    }
}

// 全局存储分页实例,以便在 onclick 中访问
window.paginationInstances = window.paginationInstances || {};
