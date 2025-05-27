'use client';

import { useState, FormEvent, useEffect, useRef } from 'react';
import { postSearchQuery } from '@/lib/api';
import { SearchResponse, ProductResult, RagContext, ChatMessage } from '@/types/definitions';
import ProductCard from './ProductCard';

const searchBarStyle: React.CSSProperties = {
  padding: '20px',
  textAlign: 'center',
  marginBottom: '20px',
  borderBottom: '1px solid #eee',
  position: 'relative',
};

const newSearchButtonContainerStyle: React.CSSProperties = {
  position: 'absolute',
  top: '20px',
  right: '20px',
  zIndex: 1,
};

const inputStyle: React.CSSProperties = {
  padding: '10px',
  fontSize: '16px',
  minWidth: '300px',
  border: '1px solid #ccc',
  flexGrow: 1,
  borderRadius: '4px',
};

const buttonStyle: React.CSSProperties = {
  padding: '10px 15px',
  fontSize: '16px',
  cursor: 'pointer',
  backgroundColor: '#0070f3',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  marginLeft: '10px',
};

const secondaryButtonStyle: React.CSSProperties = {
  padding: '10px 15px',
  fontSize: '16px',
  cursor: 'pointer',
  backgroundColor: '#6c757d',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
};

const resultsContainerStyle: React.CSSProperties = {
  marginTop: '20px',
  padding: '10px',
  border: '1px solid #eee',
  borderRadius: '4px',
  textAlign: 'left',
};

const followUpStyle: React.CSSProperties = {
  margin: '10px 0',
  padding: '10px',
  backgroundColor: '#f0f8ff',
  borderRadius: '4px',
};

const productResultsGridStyle: React.CSSProperties = {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '16px',
    justifyContent: 'center',
    padding: '20px 0',
};

const citationSectionStyle: React.CSSProperties = {
  marginTop: '15px',
  paddingTop: '10px',
  borderTop: '1px dashed #ccc',
};

const citationItemStyle: React.CSSProperties = {
  marginBottom: '10px',
  padding: '8px',
  backgroundColor: '#f9f9f9',
  borderRadius: '4px',
  fontSize: '0.9em',
};

const citationHeaderStyle: React.CSSProperties = {
  fontWeight: 'bold',
  cursor: 'pointer',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
};

const citationContentStyle: React.CSSProperties = {
  marginTop: '5px',
  paddingLeft: '10px',
  borderLeft: '2px solid #0070f3',
  whiteSpace: 'pre-wrap',
};

const searchLogContainerStyle: React.CSSProperties = {
  maxHeight: '70vh',
  border: '1px solid #ddd',
  marginTop: '50px',
  borderRadius: '4px',
  display: 'flex',
  flexDirection: 'column',
};

const messagesAreaStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  flexGrow: 1,
  overflowY: 'auto',
  padding: '10px',
};

const searchInputFormStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  padding: '10px',
  borderTop: '1px solid #ddd',
  backgroundColor: '#fff',
};

const searchMessageBaseStyle: React.CSSProperties = {
  padding: '10px 15px',
  borderRadius: '15px',
  marginBottom: '10px',
  maxWidth: '80%',
  wordWrap: 'break-word',
  position: 'relative',
};

const userMessageStyle: React.CSSProperties = {
  ...searchMessageBaseStyle,
  backgroundColor: '#0070f3',
  color: 'white',
  alignSelf: 'flex-end',
  textAlign: 'right',
};

const aiMessageStyle: React.CSSProperties = {
  ...searchMessageBaseStyle,
  backgroundColor: '#e9e9eb',
  color: '#333',
  alignSelf: 'flex-start',
};

const aiMessageContentStyle: React.CSSProperties = {
  textAlign: 'left',
};


interface AiMessageDisplayProps {
  response: SearchResponse;
}

const AiMessageDisplay: React.FC<AiMessageDisplayProps> = ({ response }) => {
  return (
    <div style={aiMessageContentStyle}>
      {response.contextual_justification && (
        <p style={{fontStyle: 'italic', color: '#555', marginBottom: '15px'}}>
          {response.contextual_justification}
        </p>
      )}

      {response.answer && (
        <div style={{marginBottom: '15px'}}>
          <h4>Answer:</h4>
          <p>{response.answer}</p>
        </div>
      )}

      {response.follow_up_questions && response.follow_up_questions.length > 0 && (
        <div style={{...followUpStyle, marginBottom: '15px'}}>
          <h4>Follow-up Questions:</h4>
          <ul>
            {response.follow_up_questions.map((q, index) => (
              <li key={index}>{q}</li>
            ))}
          </ul>
        </div>
      )}
      
      {response.results && response.results.length > 0 && (
        <div style={{marginTop: '20px'}}>
          <h4>Recommended Products:</h4>
          <div style={productResultsGridStyle}>
            {response.results.map((result: ProductResult, index: number) => (
              result && result.product ? (
                <div key={result.product.product_id + '-' + index} style={{textAlign: 'left'}}>
                  <ProductCard productResult={result} />
                </div>
              ) : null
            ))}
          </div>
        </div>
      )}

      {!response.answer &&
       (!response.follow_up_questions || response.follow_up_questions.length === 0) &&
       (!response.results || response.results.length === 0) &&
       (!response.rag_contexts || response.rag_contexts.length === 0) && (
        <p>No specific results or follow-up for your query.</p>
      )}
    </div>
  );
};

interface SearchBarProps {
  onSearchActivity: (isActive: boolean) => void;
}

export default function SearchBar({ onSearchActivity }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchLog, setSearchLog] = useState<ChatMessage[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const lastUserMessage = searchLog.filter(msg => msg.sender === 'user').pop();
  const lastAiMessage = searchLog.filter(msg => msg.sender === 'ai').pop();

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollTop = messagesEndRef.current.scrollHeight;
    }
  }, [searchLog]);

  const handleNewSearch = () => {
    setQuery('');
    setSessionId(undefined);
    setSearchLog([]);
    setError(null);
    onSearchActivity(false);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) return;

    setIsLoading(true);
    setError(null);

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: trimmedQuery,
      timestamp: new Date(),
    };
    
    setSearchLog(prevLog => [...prevLog, userMessage]);
    if (searchLog.length === 0) {
        onSearchActivity(true);
    }
    setQuery('');

    try {
      const response = await postSearchQuery({ query: trimmedQuery, session_id: sessionId });
      if (response) {
        const aiMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          sender: 'ai',
          response: response,
          timestamp: new Date(),
        };
        setSearchLog(prevLog => [...prevLog, aiMessage]);
        if (response.session_id && (!sessionId || sessionId !== response.session_id)) {
          setSessionId(response.session_id);
        }
      } else {
        setError('Failed to get search results. Please try again.');
      }
    } catch (err) {
      setError('An unexpected error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={searchBarStyle}>
      {searchLog.length > 0 && (
        <div style={newSearchButtonContainerStyle}>
          <button type="button" onClick={handleNewSearch} disabled={isLoading} style={secondaryButtonStyle}>
            New Search
          </button>
        </div>
      )}

      {searchLog.length > 0 ? (
        <div style={searchLogContainerStyle}>
          <div ref={messagesEndRef} style={messagesAreaStyle}>
            {lastUserMessage && (
              <div key={lastUserMessage.id} style={userMessageStyle}>
                {lastUserMessage.text}
              </div>
            )}
            {lastAiMessage && lastAiMessage.response && !isLoading && (
              <div key={lastAiMessage.id} style={aiMessageStyle}>
                <AiMessageDisplay response={lastAiMessage.response} />
              </div>
            )}
          </div>
          <form onSubmit={handleSubmit} style={searchInputFormStyle}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type your message..."
              style={inputStyle}
              disabled={isLoading}
            />
            <button type="submit" disabled={isLoading} style={buttonStyle}>
              {isLoading ? 'Sending...' : 'Send'}
            </button>
          </form>
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ marginTop: '20px' }}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask about products or your skin concerns..."
            style={{...inputStyle, flexGrow: 0, minWidth: '400px' }}
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading} style={buttonStyle}>
            {isLoading ? 'Searching...' : 'Start Search'}
          </button>
        </form>
      )}

      {isLoading && <p style={{marginTop: '10px', textAlign: 'center'}}>Loading response...</p>}
      {error && <p style={{ color: 'red', marginTop: '10px', textAlign: 'center' }}>{error}</p>}
    </div>
  );
}
