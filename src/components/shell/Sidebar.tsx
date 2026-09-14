'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  Activity, 
  BarChart3, 
  BrainCircuit, 
  ChevronLeft, 
  ChevronRight, 
  Cpu, 
  Database, 
  LayoutDashboard, 
  RadioTower, 
  ShieldCheck,
  X
} from 'lucide-react';

interface SidebarProps {
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
  badgeColor?: string;
}

export function Sidebar({ collapsed, setCollapsed, mobileOpen = false, onCloseMobile }: SidebarProps) {
  const pathname = usePathname();

  const navItems: NavItem[] = [
    { name: 'Command Centre', href: '/', icon: LayoutDashboard },
    { name: 'AWS Network', href: '/stations', icon: RadioTower },
    { name: 'Incidents', href: '/incidents', icon: Activity },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
    { name: 'Scientific Evidence', href: '/validation', icon: ShieldCheck },
    { name: 'Data Sources', href: '/data-sources', icon: Database },
    { name: 'Model Intelligence', href: '/model', icon: BrainCircuit },
    { name: 'System Health', href: '/system', icon: Cpu },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-40 md:hidden transition-opacity"
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 md:relative md:z-30 flex flex-col bg-white border-r border-slate-200 text-slate-700 transition-all duration-200 select-none shadow-xl md:shadow-xs ${
          mobileOpen ? 'translate-x-0 w-64' : '-translate-x-full md:translate-x-0'
        } ${collapsed ? 'md:w-16' : 'md:w-60'}`}
      >
        {/* Mobile Header with close button */}
        <div className="flex items-center justify-between p-3 border-b border-slate-100 md:hidden">
          <span className="font-bold text-xs text-slate-800 uppercase tracking-wider">Navigation</span>
          <button
            onClick={onCloseMobile}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
            aria-label="Close navigation"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation Links */}
        <div className="flex-1 py-3 px-2 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onCloseMobile}
                title={collapsed ? item.name : undefined}
                className={`group flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 font-bold border-l-4 border-blue-600 shadow-xs'
                    : 'text-slate-600 hover:bg-slate-100/70 hover:text-slate-900 border-l-4 border-transparent'
                } ${collapsed ? 'md:justify-center md:px-0' : ''}`}
              >
                <Icon
                  className={`w-4 h-4 flex-shrink-0 transition-transform group-hover:scale-110 ${
                    isActive ? 'text-blue-600' : 'text-slate-400 group-hover:text-blue-600'
                  }`}
                />

                {(!collapsed || mobileOpen) && (
                  <div className="flex-1 flex items-center justify-between overflow-hidden whitespace-nowrap">
                    <span className="truncate">{item.name}</span>
                    {item.badge && (
                      <span
                        className={`ml-2 text-[10px] font-mono px-1.5 py-0.2 rounded border ${
                          item.badgeColor || 'bg-slate-100 text-slate-700 border-slate-200'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </div>
                )}
              </Link>
            );
          })}
        </div>

        {/* Desktop Collapse Toggle Footer */}
        <div className="p-2 border-t border-slate-100 hidden md:block">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className={`w-full flex items-center gap-2 p-2 rounded-xl text-xs font-mono text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors ${
              collapsed ? 'justify-center' : 'justify-between px-3'
            }`}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {!collapsed && <span className="text-[11px] font-bold">COLLAPSE</span>}
            {collapsed ? <ChevronRight className="w-4 h-4 text-blue-600" /> : <ChevronLeft className="w-4 h-4 text-slate-400" />}
          </button>
        </div>
      </aside>
    </>
  );
}
