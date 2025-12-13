import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

// Track rehydration status
let hasHydrated = false;
export const getHasHydrated = () => hasHydrated;
export const waitForHydration = () => new Promise<void>((resolve) => {
  if (hasHydrated) {
    resolve();
    return;
  }
  const checkInterval = setInterval(() => {
    if (hasHydrated) {
      clearInterval(checkInterval);
      resolve();
    }
  }, 50);
  // Timeout after 2 seconds
  setTimeout(() => {
    clearInterval(checkInterval);
    resolve();
  }, 2000);
});

export interface TodoItem {
  id: string;
  text: string;
  done: boolean;
  createdAt: string;
  completedAt?: string;
}

export interface DataEntry {
  id: string;
  type: string; // 'exercise', 'weight', 'diet', 'custom'
  date: string;
  value: string;
  unit?: string;
  notes?: string;
}

export interface WorkspaceState {
  // Panel state
  isOpen: boolean;
  activeTab: 'notes' | 'todos' | 'data';
  
  // Notes
  notes: string;
  lastSaved: string | null;
  
  // Todos
  todos: TodoItem[];
  
  // Data tracking
  dataEntries: DataEntry[];
  
  // Actions
  setIsOpen: (open: boolean) => void;
  togglePanel: () => void;
  setActiveTab: (tab: 'notes' | 'todos' | 'data') => void;
  
  // Notes actions
  setNotes: (notes: string) => void;
  appendToNotes: (text: string) => void;
  
  // Todo actions
  addTodo: (text: string) => void;
  toggleTodo: (id: string) => void;
  deleteTodo: (id: string) => void;
  clearCompletedTodos: () => void;
  
  // Data actions
  addDataEntry: (entry: Omit<DataEntry, 'id'>) => void;
  deleteDataEntry: (id: string) => void;
  clearDataEntries: (type?: string) => void;
  
  // Export
  exportNotes: (format: 'md' | 'txt') => string;
  exportTodos: (format: 'md' | 'txt' | 'json') => string;
  exportData: (format: 'csv' | 'json', type?: string) => string;
}

const generateId = () => Math.random().toString(36).substring(2, 9);

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set, get) => ({
      // Initial state
      isOpen: false,
      activeTab: 'notes',
      notes: '',
      lastSaved: null,
      todos: [],
      dataEntries: [],
      
      // Panel actions
      setIsOpen: (open) => set({ isOpen: open }),
      togglePanel: () => set((state) => ({ isOpen: !state.isOpen })),
      setActiveTab: (tab) => set({ activeTab: tab }),
      
      // Notes actions
      setNotes: (notes) => set({ notes, lastSaved: new Date().toISOString() }),
      appendToNotes: (text) => set((state) => ({
        notes: state.notes ? `${state.notes}\n\n${text}` : text,
        lastSaved: new Date().toISOString()
      })),
      
      // Todo actions
      addTodo: (text) => set((state) => ({
        todos: [...state.todos, {
          id: generateId(),
          text,
          done: false,
          createdAt: new Date().toISOString()
        }]
      })),
      
      toggleTodo: (id) => set((state) => ({
        todos: state.todos.map(todo =>
          todo.id === id
            ? { ...todo, done: !todo.done, completedAt: !todo.done ? new Date().toISOString() : undefined }
            : todo
        )
      })),
      
      deleteTodo: (id) => set((state) => ({
        todos: state.todos.filter(todo => todo.id !== id)
      })),
      
      clearCompletedTodos: () => set((state) => ({
        todos: state.todos.filter(todo => !todo.done)
      })),
      
      // Data actions
      addDataEntry: (entry) => set((state) => ({
        dataEntries: [...state.dataEntries, { ...entry, id: generateId() }]
      })),
      
      deleteDataEntry: (id) => set((state) => ({
        dataEntries: state.dataEntries.filter(entry => entry.id !== id)
      })),
      
      clearDataEntries: (type) => set((state) => ({
        dataEntries: type
          ? state.dataEntries.filter(entry => entry.type !== type)
          : []
      })),
      
      // Export functions
      exportNotes: (format) => {
        const { notes } = get();
        if (format === 'md' || format === 'txt') {
          return notes;
        }
        return notes;
      },
      
      exportTodos: (format) => {
        const { todos } = get();
        if (format === 'json') {
          return JSON.stringify(todos, null, 2);
        }
        // Markdown/text format
        const lines = todos.map(t => `- [${t.done ? 'x' : ' '}] ${t.text}`);
        return `# Todo List\n\n${lines.join('\n')}`;
      },
      
      exportData: (format, type) => {
        const { dataEntries } = get();
        const filtered = type ? dataEntries.filter(e => e.type === type) : dataEntries;
        
        if (format === 'json') {
          return JSON.stringify(filtered, null, 2);
        }
        
        // CSV format
        if (filtered.length === 0) return 'date,type,value,unit,notes';
        const headers = 'date,type,value,unit,notes';
        const rows = filtered.map(e => 
          `${e.date},${e.type},${e.value},${e.unit || ''},${e.notes?.replace(/,/g, ';') || ''}`
        );
        return `${headers}\n${rows.join('\n')}`;
      },
    }),
    {
      name: 'galatea-workspace',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        notes: state.notes,
        todos: state.todos,
        dataEntries: state.dataEntries,
        lastSaved: state.lastSaved,
      }),
      onRehydrateStorage: () => {
        console.log('🔄 Workspace store rehydrating from localStorage...');
        return (state, error) => {
          if (error) {
            console.error('❌ Workspace rehydration error:', error);
          } else {
            console.log('✅ Workspace store hydrated!', {
              notesLength: state?.notes?.length || 0,
              todoCount: state?.todos?.length || 0,
              dataCount: state?.dataEntries?.length || 0
            });
          }
          hasHydrated = true;
        };
      },
    }
  )
);

