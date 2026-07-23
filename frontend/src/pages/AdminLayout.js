import { useState } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AdminSidebar } from '../components/AdminSidebar';
import { Toaster } from '../components/ui/sonner';
import { Menu, Building2, LogOut } from 'lucide-react';

const AdminLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/admin/login');
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <AdminSidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile top-bar — only visible below lg breakpoint */}
        <header className="lg:hidden flex items-center justify-between px-4 h-14 bg-slate-900 text-white sticky top-0 z-30 flex-shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-1.5 rounded text-slate-300 hover:text-white hover:bg-slate-700 transition-colors flex-shrink-0"
              aria-label="Open menu"
              data-testid="mobile-menu-btn"
            >
              <Menu className="w-6 h-6" />
            </button>
            <div className="flex items-center gap-2 min-w-0">
              <Building2 className="w-5 h-5 text-white/80 flex-shrink-0" />
              <span className="font-outfit text-sm font-semibold truncate">
                Lost &amp; Found Admin
              </span>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="p-1.5 rounded text-slate-300 hover:text-white hover:bg-slate-700 transition-colors flex items-center gap-1.5 text-xs flex-shrink-0 ml-2"
            title="Logout"
            data-testid="admin-mobile-logout-btn"
          >
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto">
          <div className="p-4 sm:p-6 lg:p-8">
            <Outlet />
          </div>
        </main>
      </div>

      <Toaster position="top-right" />
    </div>
  );
};

export default AdminLayout;
