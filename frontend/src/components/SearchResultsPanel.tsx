import { useState } from 'react'
import { useConversationStore, SearchResults } from '../stores/conversationStore'
import { 
  Search, 
  ExternalLink, 
  ChevronDown, 
  ChevronUp, 
  X, 
  BookmarkPlus,
  Globe,
  Sparkles
} from 'lucide-react'

interface SearchResultsPanelProps {
  results: SearchResults
  onSaveToKnowledge?: () => void
}

export function SearchResultsPanel({ results, onSaveToKnowledge }: SearchResultsPanelProps) {
  const { clearSearchResults } = useConversationStore()
  const [isExpanded, setIsExpanded] = useState(true)
  const [showSources, setShowSources] = useState(false)

  const providerIcon = results.provider === 'perplexica' ? (
    <Sparkles className="w-4 h-4 text-purple-400" />
  ) : (
    <Globe className="w-4 h-4 text-blue-400" />
  )

  const providerLabel = results.provider === 'perplexica' 
    ? 'AI-Powered Search' 
    : 'Web Search'

  return (
    <div className="w-full bg-gradient-to-br from-blue-500/5 to-purple-500/5 
                    border border-blue-500/20 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-blue-500/10 border-b border-blue-500/20">
        <button 
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors"
        >
          <Search className="w-5 h-5" />
          <span className="font-medium">Search Results</span>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>
        
        <div className="flex items-center gap-2">
          {/* Provider badge */}
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-slate-800/50 text-xs">
            {providerIcon}
            <span className="text-slate-400">{providerLabel}</span>
          </div>
          
          {/* Save to knowledge base button (future feature) */}
          {onSaveToKnowledge && (
            <button
              onClick={onSaveToKnowledge}
              className="p-1.5 rounded hover:bg-blue-500/20 text-blue-400 
                         hover:text-blue-300 transition-colors"
              title="Save to Knowledge Base"
            >
              <BookmarkPlus className="w-4 h-4" />
            </button>
          )}
          
          {/* Close button */}
          <button
            onClick={clearSearchResults}
            className="p-1.5 rounded hover:bg-slate-700/50 text-slate-400 
                       hover:text-slate-300 transition-colors"
            title="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Query */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-500">Query:</span>
            <span className="text-slate-300 font-medium">"{results.query}"</span>
          </div>
          
          {/* AI Summary */}
          {results.summary && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-purple-400">
                <Sparkles className="w-4 h-4" />
                <span className="font-medium">AI Summary</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/50 border border-purple-500/20 
                              max-h-64 overflow-y-auto">
                <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
                  {results.summary}
                </p>
              </div>
            </div>
          )}
          
          {/* Sources Toggle */}
          {results.sources.length > 0 && (
            <div className="space-y-2">
              <button
                onClick={() => setShowSources(!showSources)}
                className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
              >
                <Globe className="w-4 h-4" />
                <span className="font-medium">
                  {results.sources.length} Source{results.sources.length !== 1 ? 's' : ''}
                </span>
                {showSources ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </button>
              
              {showSources && (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {results.sources.map((source, index) => (
                    <a
                      key={index}
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block p-3 rounded-lg bg-slate-800/30 border border-slate-700/50
                                 hover:border-blue-500/30 hover:bg-slate-800/50 transition-colors group"
                    >
                      <div className="flex items-start gap-2">
                        <span className="text-xs text-slate-500 font-mono mt-0.5">
                          [{index + 1}]
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-blue-400 font-medium truncate group-hover:text-blue-300">
                              {source.title || 'Untitled'}
                            </span>
                            <ExternalLink className="w-3 h-3 text-slate-500 flex-shrink-0" />
                          </div>
                          {source.snippet && (
                            <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                              {source.snippet}
                            </p>
                          )}
                          <p className="text-xs text-slate-600 mt-1 truncate">
                            {source.url}
                          </p>
                        </div>
                      </div>
                    </a>
                  ))}
                </div>
              )}
            </div>
          )}
          
          {/* Timestamp */}
          <p className="text-xs text-slate-600 text-right">
            {new Date(results.timestamp).toLocaleTimeString()}
          </p>
        </div>
      )}
    </div>
  )
}


