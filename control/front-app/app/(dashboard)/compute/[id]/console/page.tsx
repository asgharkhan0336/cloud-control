'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
  ArrowLeft,
  Terminal,
  RefreshCw,
  Maximize2,
  Minimize2,
  Clipboard,
  AlertTriangle,
  Loader2,
  Wifi,
  WifiOff,
  Expand,
  Settings
} from 'lucide-react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { toast } from 'react-hot-toast';

interface VMInfo {
  id: number;
  name: string;
  state: 'running' | 'stopped' | 'paused';
}

interface ConsoleSession {
  url: string;
  token: string;
  expires_in: number;
}

export default function ConsolePage() {
  const params = useParams();
  const router = useRouter();
  const vmId = parseInt(params.id as string);
  
  const [isConnected, setIsConnected] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [session, setSession] = useState<ConsoleSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [clipboardText, setClipboardText] = useState('');
  
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Fetch VM info
  const { data: vm, isLoading: vmLoading } = useQuery({
    queryKey: ['vm', vmId],
    queryFn: async () => {
      const response = await apiClient.get(`/vms/${vmId}`);
      return response as VMInfo;
    },
  });

  // Request console session
  const consoleMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post(`/vms/${vmId}/console`);
      return response as ConsoleSession;
    },
    onSuccess: (data) => {
      setSession(data);
      setError(null);
      connectWebSocket(data.token);
      toast.success('Console session created');
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Failed to create console session');
      toast.error('Failed to create console session');
    },
  });

  // Connect to WebSocket
  const connectWebSocket = (token: string) => {
    const wsUrl = session?.url || `ws://${window.location.host}/console/${token}`;
    
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('Connection error');
        setIsConnected(false);
      };
      
      ws.onmessage = (event) => {
        // Handle incoming VNC data if using custom implementation
        console.log('Received message:', event.data);
      };
    } catch (err) {
      console.error('Failed to connect WebSocket:', err);
      setError('Failed to connect to console');
    }
  };

  // Initialize console
  useEffect(() => {
    if (vm?.state === 'running') {
      consoleMutation.mutate();
    }
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [vm?.state]);

  // Fullscreen toggle
  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    
    if (!isFullscreen) {
      if (containerRef.current.requestFullscreen) {
        containerRef.current.requestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
    setIsFullscreen(!isFullscreen);
  };

  // Listen for fullscreen change
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // Send clipboard text to VM
  const sendClipboard = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // Send clipboard data (implementation depends on VNC protocol)
      wsRef.current.send(JSON.stringify({ type: 'clipboard', text: clipboardText }));
      toast.success('Text sent to VM');
    }
  };

  // Paste from clipboard
  const pasteFromClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      setClipboardText(text);
      sendClipboard();
    } catch (err) {
      toast.error('Failed to read clipboard');
    }
  };

  // Reconnect console
  const reconnect = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    consoleMutation.mutate();
  };

  // Render loading state
  if (vmLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  // Render error if VM not running
  if (vm?.state !== 'running') {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <button
            onClick={() => router.back()}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Console - {vm?.name}
          </h1>
        </div>
        
        <div className="card p-12 text-center">
          <AlertTriangle className="w-16 h-16 text-yellow-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            VM is not running
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mb-6">
            Console access is only available when the VM is in running state.
          </p>
          <button
            onClick={() => router.push(`/compute/${vmId}`)}
            className="btn btn-primary"
          >
            Return to VM Details
          </button>
        </div>
      </div>
    );
  }

  // Render error if console session failed
  if (error) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <button
            onClick={() => router.back()}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Console - {vm?.name}
          </h1>
        </div>
        
        <div className="card p-12 text-center">
          <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Failed to connect
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mb-6">
            {error}
          </p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={reconnect}
              className="btn btn-primary flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Retry Connection
            </button>
            <button
              onClick={() => router.back()}
              className="btn btn-secondary"
            >
              Go Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Console - {vm?.name}
            </h1>
            <div className="flex items-center gap-3 mt-1">
              <span className={`flex items-center gap-1 text-sm ${
                isConnected ? 'text-green-600' : 'text-red-600'
              }`}>
                {isConnected ? (
                  <>
                    <Wifi className="w-4 h-4" />
                    Connected
                  </>
                ) : (
                  <>
                    <WifiOff className="w-4 h-4" />
                    Disconnected
                  </>
                )}
              </span>
              {session && (
                <span className="text-sm text-gray-500">
                  Session expires in {Math.floor(session.expires_in / 60)}:{(session.expires_in % 60).toString().padStart(2, '0')}
                </span>
              )}
            </div>
          </div>
        </div>
        
        {/* Toolbar */}
        <div className="flex items-center gap-2">
          {/* Clipboard controls */}
          <div className="flex items-center gap-1 border border-gray-200 dark:border-gray-700 rounded-lg p-1">
            <input
              type="text"
              value={clipboardText}
              onChange={(e) => setClipboardText(e.target.value)}
              placeholder="Text to send..."
              className="px-3 py-1.5 text-sm bg-transparent border-none focus:outline-none w-48"
            />
            <button
              onClick={sendClipboard}
              className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              title="Send to VM"
            >
              <Terminal className="w-4 h-4" />
            </button>
            <button
              onClick={pasteFromClipboard}
              className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              title="Paste from clipboard"
            >
              <Clipboard className="w-4 h-4" />
            </button>
          </div>
          
          <button
            onClick={reconnect}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            title="Reconnect"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          
          <button
            onClick={toggleFullscreen}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          
          <button
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {/* Console Area */}
      <div 
        ref={containerRef}
        className="flex-1 bg-gray-900 rounded-lg overflow-hidden border border-gray-700"
      >
        {consoleMutation.isPending ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Loader2 className="w-12 h-12 animate-spin text-blue-500 mx-auto mb-4" />
              <p className="text-gray-400">Establishing console connection...</p>
            </div>
          </div>
        ) : session ? (
          <iframe
            ref={iframeRef}
            src={`/novnc/vnc.html?path=ws://${window.location.host}/console/${session.token}`}
            className="w-full h-full border-0"
            allow="clipboard-read; clipboard-write"
          />
        ) : null}
      </div>
      
      {/* Keyboard shortcuts help */}
      <div className="mt-3 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-4">
        <span><kbd className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">Ctrl</kbd> + <kbd className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">Alt</kbd> + <kbd className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">Del</kbd> → Send Ctrl+Alt+Del</span>
        <span><kbd className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">Ctrl</kbd> + <kbd className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">Alt</kbd> + <kbd className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">F1</kbd> → Switch TTY</span>
      </div>
    </div>
  );
}