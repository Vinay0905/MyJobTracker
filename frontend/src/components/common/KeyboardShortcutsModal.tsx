import React from 'react';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const KeyboardShortcutsModal: React.FC<KeyboardShortcutsModalProps> = ({
  isOpen,
  onClose,
}) => {
  if (!isOpen) return null;

  const shortcuts = [
    { key: 'j / k or ↓ / ↑', desc: 'Navigate job feed up/down' },
    { key: 'Enter / Space', desc: 'Open selected job details in drawer' },
    { key: 'Esc', desc: 'Close drawer or modal' },
    { key: '/ or ⌘K', desc: 'Focus global job search input' },
    { key: '1 – 6', desc: 'Quick switch views (Radar, Constellation, Salary, Telemetry, 1-Skill, Sources)' },
    { key: 'm', desc: 'Toggle synthesized terminal sound effects' },
    { key: '?', desc: 'Toggle this keyboard shortcuts cheat sheet' },
  ];

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-surface-container-low border border-primary/40 rounded-2xl p-space-lg shadow-2xl flex flex-col gap-4 font-mono">
        <div className="flex items-center justify-between border-b border-outline-variant/60 pb-3">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-base">keyboard</span>
            <span className="text-sm font-bold text-on-surface">Vim & Terminal Ergonomics</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-surface-container text-outline hover:text-on-surface transition-colors"
          >
            <span className="material-symbols-outlined text-sm">close</span>
          </button>
        </div>

        <div className="flex flex-col gap-2.5">
          {shortcuts.map((s, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2 rounded-xl bg-surface-container border border-outline-variant/40 text-xs"
            >
              <kbd className="px-2 py-1 rounded bg-surface-container-highest border border-outline-variant font-bold text-primary text-[11px]">
                {s.key}
              </kbd>
              <span className="text-on-surface-variant text-[11px] text-right">{s.desc}</span>
            </div>
          ))}
        </div>

        <div className="pt-2 border-t border-outline-variant/40 flex justify-between items-center text-[11px] text-outline">
          <span>Press <kbd className="px-1 py-0.5 rounded bg-surface-container-highest text-white">Esc</kbd> to dismiss</span>
          <span className="text-secondary font-semibold">DevRadar v2.4</span>
        </div>
      </div>
    </div>
  );
};
