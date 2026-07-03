import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  Search,
  Package,
  Users,
  MessageSquare,
  Trash2,
  Settings,
  LogOut,
  Sparkles,
  UserCog,
  Building2,
  Shield,
  X,
} from 'lucide-react';

const navItems = [
  { to: '/admin', icon: LayoutDashboard, label: 'Dashboard', exact: true },
  { to: '/admin/lost-items', icon: Search, label: 'Lost Items' },
  { to: '/admin/found-items', icon: Package, label: 'Found Items' },
  { to: '/admin/ai-matches', icon: Sparkles, label: 'AI Matches' },
  { to: '/admin/verification-queue', icon: Shield, label: 'Verification Queue' },
  { to: '/admin/claims', icon: Package, label: 'Claims' },
  { to: '/admin/students', icon: Users, label: 'Students' },
  { to: '/admin/messages', icon: MessageSquare, label: 'Messages' },
  { to: '/admin/deleted-items', icon: Trash2, label: 'Deleted Items' },
];

const superAdminItems = [
  { to: '/admin/manage-admins', icon: UserCog, label: 'Manage Admins' },
];

export const AdminSidebar = ({ isOpen, onClose }) => {
  const { logout, isSuperAdmin, user } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    onClose?.();
    navigate('/admin/login');
  };

  return (
    <>
      {/* Dark backdrop — only visible on mobile when sidebar is open */}
      <div
        className={`fixed inset-0 bg-black/50 z-40 lg:hidden transition-opacity duration-300 ${
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sidebar panel */}
      <aside
        className={`sidebar flex flex-col fixed inset-y-0 left-0 z-50 transition-transform duration-300 ease-in-out
          lg:relative lg:translate-x-0 lg:z-auto
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}
        data-testid="admin-sidebar"
      >
        {/* Logo / Header */}
        <div className="p-4 border-b border-slate-700 flex items-center justify-between gap-2">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 bg-white/10 rounded-lg flex items-center justify-center flex-shrink-0">
              <Building2 className="w-6 h-6 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-sm font-bold text-white leading-tight font-outfit truncate">
                ST. PETERS COLLEGE
              </h1>
              <p className="text-xs text-slate-400">Lost &amp; Found Admin</p>
            </div>
          </div>
          {/* Close button — only on mobile */}
          <button
            onClick={onClose}
            className="lg:hidden flex-shrink-0 p-1.5 rounded text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 overflow-y-auto">
          <div className="px-3 mb-2">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-3">
              Main Menu
            </p>
          </div>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.exact}
              onClick={onClose}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? 'active' : ''}`
              }
              data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
            >
              <item.icon className="w-5 h-5 mr-3 flex-shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          ))}

          {isSuperAdmin && (
            <>
              <div className="px-3 mt-6 mb-2">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-3">
                  Super Admin
                </p>
              </div>
              {superAdminItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `sidebar-link ${isActive ? 'active' : ''}`
                  }
                  data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
                >
                  <item.icon className="w-5 h-5 mr-3 flex-shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </>
          )}
        </nav>

        {/* User & Settings */}
        <div className="p-4 border-t border-slate-700">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-slate-600 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-sm font-medium text-white">
                {user?.full_name?.charAt(0) || 'A'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {user?.full_name || 'Admin'}
              </p>
              <p className="text-xs text-slate-400 truncate">
                {isSuperAdmin ? 'Super Admin' : 'Admin'}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <NavLink
              to="/admin/settings"
              onClick={onClose}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm text-slate-300 hover:text-white hover:bg-slate-700 rounded-md transition-colors"
              data-testid="nav-settings"
            >
              <Settings className="w-4 h-4" />
              <span>Settings</span>
            </NavLink>
            <button
              onClick={handleLogout}
              className="flex items-center justify-center gap-2 px-3 py-2 text-sm text-slate-300 hover:text-white hover:bg-slate-700 rounded-md transition-colors"
              data-testid="logout-btn"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};
