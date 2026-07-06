"use client";

// Discord-style voice via WebRTC (P2P mesh). The provider lives at the app
// shell, so an active call keeps running while the user navigates or plays a
// game. Audio flows peer-to-peer (Opus) for high quality; large rooms should
// add an SFU (LiveKit/mediasoup) behind the same signalling.

import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
  ReactNode,
} from "react";
import { wsUrl } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const ICE = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };

interface PeerInfo {
  id: number;
  username: string;
}

interface CallState {
  room: string | null;
  peers: PeerInfo[];
  muted: boolean;
  join: (room: string) => Promise<void>;
  leave: () => void;
  toggleMute: () => void;
}

const CallContext = createContext<CallState | null>(null);

export function CallProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [room, setRoom] = useState<string | null>(null);
  const [peers, setPeers] = useState<PeerInfo[]>([]);
  const [muted, setMuted] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const localStream = useRef<MediaStream | null>(null);
  const pcs = useRef<Map<number, RTCPeerConnection>>(new Map());
  const audioEls = useRef<Map<number, HTMLAudioElement>>(new Map());

  const myId = user?.id ?? -1;

  const send = (payload: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
    }
  };

  const attachStream = useCallback((peerId: number, stream: MediaStream) => {
    let el = audioEls.current.get(peerId);
    if (!el) {
      el = document.createElement("audio");
      el.autoplay = true;
      document.body.appendChild(el);
      audioEls.current.set(peerId, el);
    }
    el.srcObject = stream;
  }, []);

  const makePc = useCallback(
    (peerId: number, username: string) => {
      const pc = new RTCPeerConnection(ICE);
      localStream.current?.getTracks().forEach((t) => pc.addTrack(t, localStream.current!));
      pc.onicecandidate = (e) => {
        if (e.candidate) send({ event: "ice", target: peerId, data: e.candidate });
      };
      pc.ontrack = (e) => attachStream(peerId, e.streams[0]);
      pcs.current.set(peerId, pc);
      setPeers((prev) =>
        prev.some((p) => p.id === peerId) ? prev : [...prev, { id: peerId, username }],
      );
      return pc;
    },
    [attachStream],
  );

  const join = useCallback(
    async (target: string) => {
      if (room) return;
      localStream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
      const ws = new WebSocket(wsUrl(`/ws/voice/${target}/`));
      wsRef.current = ws;
      setRoom(target);

      ws.onmessage = async (ev) => {
        const m = JSON.parse(ev.data);
        if (m.peer_id === myId) return;

        if (m.event === "peer-join") {
          // We were here first: initiate the offer to the newcomer.
          const pc = makePc(m.peer_id, m.peer);
          const offer = await pc.createOffer();
          await pc.setLocalDescription(offer);
          send({ event: "offer", target: m.peer_id, data: offer });
        } else if (m.event === "offer" && m.target === myId) {
          const pc = makePc(m.peer_id, m.peer);
          await pc.setRemoteDescription(m.data);
          const answer = await pc.createAnswer();
          await pc.setLocalDescription(answer);
          send({ event: "answer", target: m.peer_id, data: answer });
        } else if (m.event === "answer" && m.target === myId) {
          await pcs.current.get(m.peer_id)?.setRemoteDescription(m.data);
        } else if (m.event === "ice" && m.target === myId) {
          try {
            await pcs.current.get(m.peer_id)?.addIceCandidate(m.data);
          } catch {
            /* ignore */
          }
        } else if (m.event === "peer-leave") {
          pcs.current.get(m.peer_id)?.close();
          pcs.current.delete(m.peer_id);
          audioEls.current.get(m.peer_id)?.remove();
          audioEls.current.delete(m.peer_id);
          setPeers((prev) => prev.filter((p) => p.id !== m.peer_id));
        }
      };
    },
    [room, myId, makePc],
  );

  const leave = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    pcs.current.forEach((pc) => pc.close());
    pcs.current.clear();
    audioEls.current.forEach((el) => el.remove());
    audioEls.current.clear();
    localStream.current?.getTracks().forEach((t) => t.stop());
    localStream.current = null;
    setPeers([]);
    setRoom(null);
    setMuted(false);
  }, []);

  const toggleMute = useCallback(() => {
    const track = localStream.current?.getAudioTracks()[0];
    if (track) {
      track.enabled = !track.enabled;
      setMuted(!track.enabled);
    }
  }, []);

  return (
    <CallContext.Provider value={{ room, peers, muted, join, leave, toggleMute }}>
      {children}
      {room && <CallBar />}
    </CallContext.Provider>
  );
}

function CallBar() {
  const { room, peers, muted, leave, toggleMute } = useCall();
  return (
    <div className="fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-full border border-neutral-700 bg-neutral-900/95 px-4 py-2 text-sm shadow-lg backdrop-blur">
      <span className="flex h-2 w-2 rounded-full bg-emerald-400" />
      <span className="font-medium">In call · #{room}</span>
      <span className="text-neutral-400">{peers.length + 1} connected</span>
      <button
        onClick={toggleMute}
        className="rounded-full border border-neutral-700 px-3 py-1 hover:bg-neutral-800"
      >
        {muted ? "Unmute" : "Mute"}
      </button>
      <button
        onClick={leave}
        className="rounded-full bg-red-500 px-3 py-1 font-medium text-white hover:bg-red-600"
      >
        Leave
      </button>
    </div>
  );
}

export function useCall() {
  const ctx = useContext(CallContext);
  if (!ctx) throw new Error("useCall must be used within CallProvider");
  return ctx;
}
