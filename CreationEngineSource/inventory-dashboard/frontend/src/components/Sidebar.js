export default function Sidebar() {
  const menuItems = [
    { name: 'Dashboard', icon: '📊', active: true },
    { name: 'Inventory', icon: '📦', active: false },
    { name: 'Analytics', icon: '📈', active: false },
    { name: 'Reports', icon: '📄', active: false },
    { name: 'Settings', icon: '⚙️', active: false },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-icon" style={{ filter: 'drop-shadow(0 0 8px rgba(99, 102, 241, 0.5))' }}>📦</div>
        <span className="logo-text">Creator<span className="text-highlight" style={{ textShadow: '0 0 10px rgba(99, 102, 241, 0.5)' }}>Inventory</span></span>
      </div>

      <nav className="sidebar-nav">
        <ul className="nav-list">
          {menuItems.map((item) => (
            <li key={item.name} className={`nav-item ${item.active ? 'active' : ''}`}>
              <a href="#" className="nav-link">
                <span className="nav-icon" style={{ color: item.active ? 'var(--accent-cyan)' : 'inherit' }}>{item.icon}</span>
                <span className="nav-text">{item.name}</span>
                {item.active && <div className="active-indicator" style={{ boxShadow: '0 0 15px var(--accent-cyan)', background: 'var(--accent-cyan)' }} />}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <div className="sidebar-footer">
        <div className="user-profile">
          <div className="user-avatar">AD</div>
          <div className="user-info">
            <span className="user-name">Admin User</span>
            <span className="user-role">Warehouse Mgr</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
