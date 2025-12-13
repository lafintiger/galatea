import { useState, useRef, useEffect } from 'react';
import { 
  FileText, 
  CheckSquare, 
  BarChart3,
  Plus,
  X,
  Check,
  PanelRightClose
} from 'lucide-react';
import { useWorkspaceStore, TodoItem, DataEntry } from '../stores/workspaceStore';

// Simple markdown-ish textarea editor (can swap for TipTap/CodeMirror later)
function NotesEditor() {
  const { notes, setNotes, lastSaved, exportNotes } = useWorkspaceStore();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  const handleExport = (format: 'md' | 'txt') => {
    const content = exportNotes(format);
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `gala-notes.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-2 text-xs text-gray-500">
        <span>
          {lastSaved ? `Saved ${new Date(lastSaved).toLocaleTimeString()}` : 'Not saved'}
        </span>
        <div className="flex gap-1">
          <button
            onClick={() => handleExport('md')}
            className="px-2 py-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
            title="Export as Markdown"
          >
            .md
          </button>
          <button
            onClick={() => handleExport('txt')}
            className="px-2 py-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
            title="Export as Text"
          >
            .txt
          </button>
        </div>
      </div>
      <textarea
        ref={textareaRef}
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="# My Notes&#10;&#10;Write anything here... Gala can add notes too!&#10;&#10;- Use markdown formatting&#10;- Create lists&#10;- **Bold** and *italic*"
        className="flex-1 w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-gray-200 
                   placeholder-gray-500 resize-none focus:outline-none focus:border-cyan-500/50
                   font-mono text-sm leading-relaxed"
        spellCheck
      />
    </div>
  );
}

function TodoList() {
  const { todos, addTodo, toggleTodo, deleteTodo, clearCompletedTodos, exportTodos } = useWorkspaceStore();
  const [newTodo, setNewTodo] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleAdd = () => {
    if (newTodo.trim()) {
      addTodo(newTodo.trim());
      setNewTodo('');
      inputRef.current?.focus();
    }
  };

  const handleExport = (format: 'md' | 'json') => {
    const content = exportTodos(format);
    const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `gala-todos.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const pending = todos.filter(t => !t.done);
  const completed = todos.filter(t => t.done);

  return (
    <div className="flex flex-col h-full">
      {/* Add todo input */}
      <div className="flex gap-2 mb-3">
        <input
          ref={inputRef}
          type="text"
          value={newTodo}
          onChange={(e) => setNewTodo(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          placeholder="Add a task..."
          className="flex-1 bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-sm
                     text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500/50"
        />
        <button
          onClick={handleAdd}
          disabled={!newTodo.trim()}
          className="p-2 bg-cyan-500/20 text-cyan-400 rounded-lg hover:bg-cyan-500/30 
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Plus size={18} />
        </button>
      </div>

      {/* Todo list */}
      <div className="flex-1 overflow-y-auto space-y-1">
        {pending.length === 0 && completed.length === 0 ? (
          <div className="text-center text-gray-500 text-sm py-8">
            No tasks yet. Add one above or say<br/>
            <span className="text-cyan-400">"Gala, add todo: ..."</span>
          </div>
        ) : (
          <>
            {/* Pending todos */}
            {pending.map((todo) => (
              <TodoItemRow key={todo.id} todo={todo} onToggle={toggleTodo} onDelete={deleteTodo} />
            ))}
            
            {/* Completed section */}
            {completed.length > 0 && (
              <>
                <div className="flex items-center justify-between pt-3 pb-1 border-t border-gray-700/50 mt-2">
                  <span className="text-xs text-gray-500">Completed ({completed.length})</span>
                  <button
                    onClick={clearCompletedTodos}
                    className="text-xs text-gray-500 hover:text-red-400 transition-colors"
                  >
                    Clear
                  </button>
                </div>
                {completed.map((todo) => (
                  <TodoItemRow key={todo.id} todo={todo} onToggle={toggleTodo} onDelete={deleteTodo} />
                ))}
              </>
            )}
          </>
        )}
      </div>

      {/* Export buttons */}
      <div className="flex justify-end gap-1 mt-2 pt-2 border-t border-gray-700/50">
        <button
          onClick={() => handleExport('md')}
          className="px-2 py-1 text-xs text-gray-400 hover:text-white hover:bg-gray-700 rounded"
        >
          Export .md
        </button>
        <button
          onClick={() => handleExport('json')}
          className="px-2 py-1 text-xs text-gray-400 hover:text-white hover:bg-gray-700 rounded"
        >
          Export .json
        </button>
      </div>
    </div>
  );
}

function TodoItemRow({ 
  todo, 
  onToggle, 
  onDelete 
}: { 
  todo: TodoItem; 
  onToggle: (id: string) => void; 
  onDelete: (id: string) => void;
}) {
  return (
    <div className={`flex items-center gap-2 p-2 rounded-lg group transition-colors
                     ${todo.done ? 'bg-gray-800/30' : 'bg-gray-800/50 hover:bg-gray-700/50'}`}>
      <button
        onClick={() => onToggle(todo.id)}
        className={`w-5 h-5 rounded border flex items-center justify-center transition-colors
                    ${todo.done 
                      ? 'bg-green-500/20 border-green-500/50 text-green-400' 
                      : 'border-gray-600 hover:border-cyan-500/50'}`}
      >
        {todo.done && <Check size={12} />}
      </button>
      <span className={`flex-1 text-sm ${todo.done ? 'text-gray-500 line-through' : 'text-gray-200'}`}>
        {todo.text}
      </span>
      <button
        onClick={() => onDelete(todo.id)}
        className="p-1 text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
      >
        <X size={14} />
      </button>
    </div>
  );
}

function DataTracker() {
  const { dataEntries, addDataEntry, deleteDataEntry, clearDataEntries, exportData } = useWorkspaceStore();
  const [showAddForm, setShowAddForm] = useState(false);
  const [newEntry, setNewEntry] = useState<Partial<DataEntry>>({
    type: 'exercise',
    date: new Date().toISOString().split('T')[0],
    value: '',
    unit: 'minutes',
    notes: ''
  });

  const dataTypes = [
    { value: 'exercise', label: '🏃 Exercise', defaultUnit: 'minutes' },
    { value: 'weight', label: '⚖️ Weight', defaultUnit: 'lbs' },
    { value: 'diet', label: '🍎 Diet', defaultUnit: 'calories' },
    { value: 'sleep', label: '😴 Sleep', defaultUnit: 'hours' },
    { value: 'water', label: '💧 Water', defaultUnit: 'oz' },
    { value: 'custom', label: '📊 Custom', defaultUnit: '' },
  ];

  const handleAdd = () => {
    if (newEntry.value && newEntry.type && newEntry.date) {
      addDataEntry({
        type: newEntry.type,
        date: newEntry.date,
        value: newEntry.value,
        unit: newEntry.unit,
        notes: newEntry.notes
      });
      setNewEntry({
        type: newEntry.type,
        date: new Date().toISOString().split('T')[0],
        value: '',
        unit: newEntry.unit,
        notes: ''
      });
      setShowAddForm(false);
    }
  };

  const handleExport = (format: 'csv' | 'json') => {
    const content = exportData(format);
    const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `gala-data.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Group entries by type
  const grouped = dataEntries.reduce((acc, entry) => {
    if (!acc[entry.type]) acc[entry.type] = [];
    acc[entry.type].push(entry);
    return acc;
  }, {} as Record<string, DataEntry[]>);

  return (
    <div className="flex flex-col h-full">
      {/* Add button / form */}
      {!showAddForm ? (
        <button
          onClick={() => setShowAddForm(true)}
          className="flex items-center justify-center gap-2 w-full p-2 mb-3 bg-cyan-500/20 
                     text-cyan-400 rounded-lg hover:bg-cyan-500/30 transition-colors text-sm"
        >
          <Plus size={16} /> Log Data
        </button>
      ) : (
        <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 mb-3 space-y-2">
          <div className="flex gap-2">
            <select
              value={newEntry.type}
              onChange={(e) => {
                const type = dataTypes.find(t => t.value === e.target.value);
                setNewEntry({ ...newEntry, type: e.target.value, unit: type?.defaultUnit || '' });
              }}
              className="flex-1 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200"
            >
              {dataTypes.map(t => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <input
              type="date"
              value={newEntry.date}
              onChange={(e) => setNewEntry({ ...newEntry, date: e.target.value })}
              className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200"
            />
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={newEntry.value}
              onChange={(e) => setNewEntry({ ...newEntry, value: e.target.value })}
              placeholder="Value (e.g., 30)"
              className="flex-1 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm 
                         text-gray-200 placeholder-gray-500"
            />
            <input
              type="text"
              value={newEntry.unit}
              onChange={(e) => setNewEntry({ ...newEntry, unit: e.target.value })}
              placeholder="Unit"
              className="w-20 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm 
                         text-gray-200 placeholder-gray-500"
            />
          </div>
          <input
            type="text"
            value={newEntry.notes}
            onChange={(e) => setNewEntry({ ...newEntry, notes: e.target.value })}
            placeholder="Notes (optional)"
            className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm 
                       text-gray-200 placeholder-gray-500"
          />
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setShowAddForm(false)}
              className="px-3 py-1 text-sm text-gray-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              onClick={handleAdd}
              disabled={!newEntry.value}
              className="px-3 py-1 text-sm bg-cyan-500/20 text-cyan-400 rounded 
                         hover:bg-cyan-500/30 disabled:opacity-50"
            >
              Add
            </button>
          </div>
        </div>
      )}

      {/* Data entries */}
      <div className="flex-1 overflow-y-auto space-y-3">
        {Object.keys(grouped).length === 0 ? (
          <div className="text-center text-gray-500 text-sm py-8">
            No data logged yet.<br/>
            Track exercise, weight, diet, and more!<br/>
            <span className="text-cyan-400">"Gala, log 30 minutes exercise"</span>
          </div>
        ) : (
          Object.entries(grouped).map(([type, entries]) => (
            <div key={type} className="bg-gray-800/30 rounded-lg p-2">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-300 capitalize">
                  {dataTypes.find(t => t.value === type)?.label || type}
                </span>
                <button
                  onClick={() => clearDataEntries(type)}
                  className="text-xs text-gray-500 hover:text-red-400"
                >
                  Clear
                </button>
              </div>
              <div className="space-y-1">
                {entries.slice(-5).reverse().map((entry) => (
                  <div key={entry.id} className="flex items-center justify-between text-xs group">
                    <span className="text-gray-500">{entry.date}</span>
                    <span className="text-gray-200">{entry.value} {entry.unit}</span>
                    {entry.notes && <span className="text-gray-500 truncate max-w-[100px]">{entry.notes}</span>}
                    <button
                      onClick={() => deleteDataEntry(entry.id)}
                      className="p-1 text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100"
                    >
                      <X size={12} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Export buttons */}
      <div className="flex justify-end gap-1 mt-2 pt-2 border-t border-gray-700/50">
        <button
          onClick={() => handleExport('csv')}
          className="px-2 py-1 text-xs text-gray-400 hover:text-white hover:bg-gray-700 rounded"
        >
          Export .csv
        </button>
        <button
          onClick={() => handleExport('json')}
          className="px-2 py-1 text-xs text-gray-400 hover:text-white hover:bg-gray-700 rounded"
        >
          Export .json
        </button>
      </div>
    </div>
  );
}

export default function WorkspacePanel() {
  const { isOpen, activeTab, setIsOpen, setActiveTab } = useWorkspaceStore();

  const tabs = [
    { id: 'notes' as const, label: 'Notes', icon: FileText },
    { id: 'todos' as const, label: 'Todos', icon: CheckSquare },
    { id: 'data' as const, label: 'Data', icon: BarChart3 },
  ];

  return (
    <>
      {/* Panel */}
      <div
        className={`fixed top-0 right-0 h-full bg-gray-900/95 backdrop-blur-sm border-l border-cyan-500/20
                    shadow-2xl shadow-cyan-500/5 transition-all duration-300 z-40
                    ${isOpen ? 'w-80 translate-x-0' : 'w-0 translate-x-full'}`}
      >
        {isOpen && (
          <div className="flex flex-col h-full p-4">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-cyan-400">Workspace</h2>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
                title="Close Workspace"
              >
                <PanelRightClose size={18} />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 mb-4">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors
                              ${activeTab === tab.id
                                ? 'bg-cyan-500/20 text-cyan-400'
                                : 'text-gray-400 hover:text-white hover:bg-gray-800'}`}
                >
                  <tab.icon size={14} />
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden">
              {activeTab === 'notes' && <NotesEditor />}
              {activeTab === 'todos' && <TodoList />}
              {activeTab === 'data' && <DataTracker />}
            </div>
          </div>
        )}
      </div>

      {/* Backdrop (mobile) */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
}

