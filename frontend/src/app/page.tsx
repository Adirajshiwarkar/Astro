"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Compass,
  MessageSquare,
  FileText,
  Sliders,
  Calendar,
  LogOut,
  User as UserIcon,
  Star,
  Send,
  Plus,
  Loader2,
  Upload,
  CheckCircle,
  HelpCircle,
  AlertTriangle,
  ChevronRight,
  ChevronDown,
  TrendingUp,
  Workflow
} from "lucide-react";
import styles from "./page.module.css";

// --- Types ---
interface Placement {
  sign: string;
  degree: number;
  house: number;
  is_retrograde?: boolean;
}

interface Placements {
  [planet: string]: Placement;
}

interface ActiveSignal {
  signal_id: string;
  domain: string;
  signal_type: string;
  strength: number;
  timeframe: string;
  source_system?: string;
  description?: string;
}

interface TimelineInterval {
  start_date: string;
  end_date: string;
  active_signals: ActiveSignal[];
}

interface Timeline {
  total_intervals: number;
  intervals: TimelineInterval[];
}

interface Scenario {
  scenario_id: string;
  domain: string;
  timeframe: string;
  support_score: number;
  evidence: string[];
  supporting_signals: string[];
  conflicting_signals: string[];
  uncertainty: string;
}

interface PredictionResponse {
  prediction_id: string;
  system: string;
  timeframe: string;
  timeline: Timeline;
  scenarios: Scenario[];
  created_at: string;
}

interface Message {
  sender: "user" | "assistant";
  text: string;
  time: string;
}

interface Conversation {
  conversation_id: string;
  title: string;
  updated_at: string;
}

// Map Western signs to their index for polar math
const SIGN_ORDER = [
  "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
  "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
];

// Humanized domain titles & theme colors
const DOMAIN_MAP: { [key: string]: { label: string; color: string } } = {
  PERSONAL_DEVELOPMENT: { label: "Personal Growth & Vitality", color: "#e6c280" },
  CAREER: { label: "Career & Leadership", color: "#c5a880" },
  FINANCE: { label: "Wealth & Finance", color: "#8ea4c0" },
  RELATIONSHIP: { label: "Relationships & Harmony", color: "#e8b0b8" },
  HEALTH: { label: "Wellness & Balance", color: "#a5c0b0" },
};

// Mappings for planet colors & abbreviations
const PLANET_META: { [key: string]: { label: string; color: string } } = {
  sun: { label: "Su", color: "#e6c280" },
  moon: { label: "Mo", color: "#b5c5d0" },
  mercury: { label: "Me", color: "#a5c0b0" },
  venus: { label: "Ve", color: "#e8b0b8" },
  mars: { label: "Ma", color: "#d87d7d" },
  jupiter: { label: "Ju", color: "#dfc299" },
  saturn: { label: "Sa", color: "#a39f96" },
  uranus: { label: "Ur", color: "#8ea4c0" },
  neptune: { label: "Ne", color: "#87afb8" },
  pluto: { label: "Pl", color: "#a59bb0" },
  ascendant: { label: "Asc", color: "#c5a880" },
  midheaven: { label: "MC", color: "#c5a880" }
};

export default function Home() {
  // Navigation & Tab State
  const [activeTab, setActiveTab] = useState<"dashboard" | "chart-calc" | "upload" | "chat" | "settings">("dashboard");

  // Auth State
  const [token, setToken] = useState<string | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [currentUser, setCurrentUser] = useState<{ email: string } | null>(null);

  // Chart Calculation State
  const [birthDate, setBirthDate] = useState("1990-01-01");
  const [birthTime, setBirthTime] = useState("12:00:00");
  const [birthPlace, setBirthPlace] = useState("New York, NY");
  const [birthLat, setBirthLat] = useState("40.7128");
  const [birthLon, setBirthLon] = useState("-74.0060");
  const [birthTz, setBirthTz] = useState("America/New_York");
  const [birthDst, setBirthDst] = useState(false);
  const [calculationSystem, setCalculationSystem] = useState<"Western" | "Vedic">("Western");
  const [isCalculating, setIsCalculating] = useState(false);

  // Placements & Calculations Output
  const [placements, setPlacements] = useState<Placements | null>(null);
  const [currentChartId, setCurrentChartId] = useState<string | null>(null);

  // Predictions State
  const [forecastTimeframe, setForecastTimeframe] = useState<"weekly" | "monthly">("monthly");
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);

  // Chat State
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: "assistant",
      text: "Hello! Ask me any questions about your natal chart, transit alignments, or forecast timelines. I will query the astrological library to give you a personalized reading.",
      time: "Just now"
    }
  ]);
  const [chatMessageInput, setChatMessageInput] = useState("");
  const [isSendingMessage, setIsSendingMessage] = useState(false);

  // OCR Upload State
  const [ocrProgress, setOcrProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [ocrResults, setOcrResults] = useState<string | null>(null);

  // Profile Settings State
  const [firstName, setFirstName] = useState("Jane");
  const [lastName, setLastName] = useState("Doe");
  const [currentLocation, setCurrentLocation] = useState("New York, NY");

  // Feedback State
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [feedbackItemType, setFeedbackItemType] = useState("prediction");
  const [feedbackRating, setFeedbackRating] = useState(5);
  const [feedbackComment, setFeedbackComment] = useState("");

  // Toasts
  const [toasts, setToasts] = useState<{ id: string; message: string; type: "success" | "error" }[]>([]);

  // Refs & Chat Scroll state
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);

  // Handle scroll events in chat messages container
  const handleChatScroll = () => {
    if (!chatContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
    const isScrolledUp = scrollHeight - scrollTop - clientHeight > 60;
    setShowScrollBottom(isScrolledUp);
  };

  const scrollToBottom = () => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: "smooth"
      });
    }
  };

  // Load Auth Token & User Session from localStorage on start
  useEffect(() => {
    const savedToken = localStorage.getItem("astro_token");
    const savedEmail = localStorage.getItem("astro_user_email");
    if (savedToken) {
      setToken(savedToken);
      if (savedEmail) {
        setCurrentUser({ email: savedEmail });
        setAuthEmail(savedEmail);
      }
      fetchProfile(savedToken);
      fetchConversations(savedToken);
    } else {
      // Pre-fill demo user credentials for seamless 1-click login
      setAuthEmail("adirajshiwarkarinfograins@gmail.com");
      setAuthPassword("Info@1234");
    }
  }, []);

  // Scroll to bottom of chat when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Show a toast message
  const showToast = (message: string, type: "success" | "error" = "success") => {
    const id = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  // --- API Calls ---

  const fetchProfile = async (authToken: string) => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/profile", {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        setFirstName(data.first_name || "");
        setLastName(data.last_name || "");
        setCurrentLocation(data.current_location || "");
        setCurrentUser({ email: data.email || "user@example.com" });
        localStorage.setItem("astro_user_email", data.email || "user@example.com");

        if (data.birth_data) {
          setBirthDate(data.birth_data.date_of_birth || "1990-01-01");
          setBirthTime(data.birth_data.birth_time || "12:00:00");
          setBirthPlace(data.birth_data.birth_place || "New York, NY");
          setBirthLat(data.birth_data.latitude?.toString() || "40.7128");
          setBirthLon(data.birth_data.longitude?.toString() || "-74.0060");
          setBirthTz(data.birth_data.timezone || "America/New_York");
          setBirthDst(data.birth_data.dst_handling || false);
        }
      } else if (res.status === 401) {
        setToken(null);
        localStorage.removeItem("astro_token");
        localStorage.removeItem("astro_user_email");
        setShowAuthModal(true);
      }
    } catch {
      showToast("Could not fetch user profile details.", "error");
    }
  };

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const endpoint = authMode === "login" ? "login" : "register";
    try {
      let body;
      let headers: HeadersInit = { "Content-Type": "application/json" };

      if (authMode === "login") {
        // OAuth2 Password Grant Form Data
        const params = new URLSearchParams();
        params.append("username", authEmail);
        params.append("password", authPassword);
        body = params;
        headers = { "Content-Type": "application/x-www-form-urlencoded" };
      } else {
        body = JSON.stringify({ email: authEmail, password: authPassword });
      }

      const res = await fetch(`http://localhost:8000/api/v1/auth/${endpoint}`, {
        method: "POST",
        headers,
        body,
      });

      if (res.ok) {
        const data = await res.json();
        const accessToken = data.access_token;
        setToken(accessToken);
        setCurrentUser({ email: authEmail });
        localStorage.setItem("astro_token", accessToken);
        localStorage.setItem("astro_user_email", authEmail);
        setShowAuthModal(false);
        showToast(authMode === "login" ? "Welcome back!" : "Registration successful!");
        fetchProfile(accessToken);
        fetchConversations(accessToken);
      } else {
        const err = await res.json();
        showToast(err.detail || "Authentication failed.", "error");
      }
    } catch {
      showToast("Authentication request failed.", "error");
    }
  };

  const handleLogout = () => {
    setToken(null);
    setCurrentUser(null);
    localStorage.removeItem("astro_token");
    localStorage.removeItem("astro_user_email");
    setPlacements(null);
    setTimeline(null);
    setScenarios([]);
    showToast("Successfully logged out.");
  };

  // Submit Chart Calculation
  const handleCalculateChart = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setShowAuthModal(true);
      showToast("Please log in to calculate custom charts.", "error");
      return;
    }
    setIsCalculating(true);
    try {
      const calcPayload = {
        system: calculationSystem,
        birth_data: {
          date_of_birth: birthDate,
          birth_time: birthTime,
          birth_place: birthPlace,
          latitude: parseFloat(birthLat),
          longitude: parseFloat(birthLon),
          timezone: birthTz,
          dst_handling: birthDst,
          timezone_source: "manual",
          coordinate_source: "manual",
          calculation_metadata: {}
        }
      };

      const res = await fetch("http://localhost:8000/api/v1/charts/calculate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(calcPayload)
      });

      if (res.ok) {
        const data = await res.json();
        setPlacements(data.placements);
        setCurrentChartId(data.chart_id);
        showToast("Celestial chart computed successfully!");

        // Save birth data to user profile
        await fetch("http://localhost:8000/api/v1/profile/birth-data", {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify(calcPayload.birth_data)
        });

        // Trigger prediction generation
        generateForecast(data.chart_id);
        setActiveTab("dashboard");
      } else if (res.status === 401) {
        setToken(null);
        localStorage.removeItem("astro_token");
        setShowAuthModal(true);
        showToast("Session expired. Please log in again.", "error");
      } else {
        const err = await res.json();
        showToast(err.detail || "Chart calculation failed.", "error");
      }
    } catch {
      showToast("Chart calculation failed.", "error");
    } finally {
      setIsCalculating(false);
    }
  };

  // Generate forecasting timeline & scenarios
  const generateForecast = async (chartId: string) => {
    if (!token) return;
    try {
      const predPayload = {
        system: calculationSystem,
        timeframe: forecastTimeframe,
        birth_data: {
          date_of_birth: birthDate,
          birth_time: birthTime,
          birth_place: birthPlace,
          latitude: parseFloat(birthLat),
          longitude: parseFloat(birthLon),
          timezone: birthTz,
          dst_handling: birthDst,
          timezone_source: "manual",
          coordinate_source: "manual",
          calculation_metadata: {}
        }
      };

      const res = await fetch("http://localhost:8000/api/v1/predictions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(predPayload)
      });

      if (res.ok) {
        const data = await res.json();
        setTimeline(data.timeline);
        setScenarios(data.scenarios);
      }
    } catch {
      showToast("Could not retrieve forecasting timeline.", "error");
    }
  };

  // Update Forecast when timeframe changes
  useEffect(() => {
    if (currentChartId) {
      generateForecast(currentChartId);
    }
  }, [forecastTimeframe]);

  // Fetch Conversation History
  const fetchConversations = async (authToken: string) => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/conversations?limit=10&offset=0", {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setConversations(data.conversations || []);
      } else if (res.status === 401) {
        setToken(null);
        localStorage.removeItem("astro_token");
        setShowAuthModal(true);
      }
    } catch {
      // Quiet fail for initial load if DB not fully seeded
    }
  };

  // Send Chat Message
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatMessageInput.trim()) return;
    if (!token) {
      setShowAuthModal(true);
      showToast("Authentication required to consult the advisor.", "error");
      return;
    }

    const userMsg = chatMessageInput;
    setMessages((prev) => [...prev, { sender: "user", text: userMsg, time: "Just now" }]);
    setChatMessageInput("");
    setIsSendingMessage(true);

    try {
      const chatPayload = {
        conversation_id: currentConversationId,
        message: userMsg,
        system_preference: calculationSystem
      };

      const res = await fetch("http://localhost:8000/api/v1/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(chatPayload)
      });

      if (res.ok) {
        const data = await res.json();
        const fullText = (data.response_message || "").replace(/\*\*/g, "");
        if (data.conversation_id && !currentConversationId) {
          setCurrentConversationId(data.conversation_id);
          fetchConversations(token);
        }

        // Live Streaming / Typewriter Effect
        setIsSendingMessage(false);
        setMessages((prev) => [...prev, { sender: "assistant", text: "", time: "Just now" }]);

        let index = 0;
        const chunkSize = 5;
        const interval = setInterval(() => {
          index += chunkSize;
          const currentChunk = fullText.slice(0, index);
          setMessages((prev) => {
            const updated = [...prev];
            if (updated.length > 0) {
              updated[updated.length - 1] = {
                sender: "assistant",
                text: currentChunk,
                time: "Just now"
              };
            }
            return updated;
          });
          chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });

          if (index >= fullText.length) {
            clearInterval(interval);
          }
        }, 18);

        return;
      } else if (res.status === 401) {
        setToken(null);
        localStorage.removeItem("astro_token");
        setShowAuthModal(true);
        showToast("Session expired. Please log in again to continue chat.", "error");
      } else {
        showToast("Error processing chat message.", "error");
      }
    } catch {
      showToast("Could not send chat message.", "error");
    } finally {
      setIsSendingMessage(false);
    }
  };

  // Start a new chat
  const handleStartNewChat = () => {
    setCurrentConversationId(null);
    setMessages([
      {
        sender: "assistant",
        text: "Hello! Ask me any questions about your natal chart, transit alignments, or forecast timelines. I will query the astrological library to give you a personalized reading.",
        time: "Just now"
      }
    ]);
  };

  // OCR Upload File Submit
  const handleFileUpload = async (file: File) => {
    setIsUploading(true);
    setOcrProgress(15);
    try {
      const formData = new FormData();
      formData.append("file", file);

      setOcrProgress(45);
      const res = await fetch("http://localhost:8000/api/v1/charts/upload", {
        method: "POST",
        body: formData
      });

      setOcrProgress(80);
      if (res.ok) {
        const data = await res.json();
        setOcrResults(JSON.stringify(data.chart_data, null, 2));
        showToast("Chart document scanned successfully!");
      } else {
        const err = await res.json();
        showToast(err.detail || "Scanning failed.", "error");
      }
    } catch {
      showToast("Chart scan request failed.", "error");
    } finally {
      setIsUploading(false);
      setOcrProgress(0);
    }
  };

  // Submit Profile Updates
  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    try {
      const res = await fetch("http://localhost:8000/api/v1/profile", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          first_name: firstName,
          last_name: lastName,
          current_location: currentLocation
        })
      });
      if (res.ok) {
        showToast("Profile settings saved.");
      } else {
        showToast("Failed to save profile settings.", "error");
      }
    } catch {
      showToast("Error updating profile settings.", "error");
    }
  };

  // Submit Feedback
  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      showToast("Authentication required.", "error");
      return;
    }
    try {
      const res = await fetch("http://localhost:8000/api/v1/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          item_type: feedbackItemType,
          item_id: currentChartId || "00000000-0000-0000-0000-000000000000",
          rating: feedbackRating,
          comment: feedbackComment
        })
      });
      if (res.ok) {
        showToast("Thank you for your alignment feedback!");
        setShowFeedbackModal(false);
        setFeedbackComment("");
      } else {
        showToast("Could not submit feedback.", "error");
      }
    } catch {
      showToast("Error submitting feedback.", "error");
    }
  };

  // --- SVG Chart Renderers ---

  const renderWesternChart = (placementsData: Placements) => {
    const size = 320;
    const center = size / 2;
    const r = 130;

    // Coordinates mapping
    const getCoordinates = (angleRad: number, radius: number) => {
      const x = center + radius * Math.cos(angleRad);
      const y = center + radius * Math.sin(angleRad);
      return { x, y };
    };

    const planets = Object.keys(placementsData).filter(p => PLANET_META[p]);

    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="chart-svg">
        <defs>
          <radialGradient id="skyGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#1e1e19" />
            <stop offset="100%" stopColor="#121210" />
          </radialGradient>
        </defs>

        {/* Background & Rings */}
        <circle cx={center} cy={center} r={r} fill="url(#skyGrad)" stroke="var(--border-color)" strokeWidth="2" />
        <circle cx={center} cy={center} r={r - 30} fill="none" stroke="var(--border-color)" strokeWidth="1" />
        <circle cx={center} cy={center} r={r - 90} fill="none" stroke="var(--border-color)" strokeWidth="1" strokeDasharray="3,3" />

        {/* 12 House Sectors */}
        {Array.from({ length: 12 }).map((_, i) => {
          const angle = (i * 30) * (Math.PI / 180);
          const outer = getCoordinates(angle, r);
          const inner = getCoordinates(angle, r - 30);
          const textPos = getCoordinates(angle + (15 * Math.PI / 180), r - 15);

          return (
            <g key={i}>
              <line x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y} stroke="var(--border-color)" strokeWidth="1" />
              <text
                x={textPos.x}
                y={textPos.y + 4}
                fill="var(--text-muted)"
                fontSize="8"
                textAnchor="middle"
                fontFamily="var(--font-sans)"
              >
                {SIGN_ORDER[i].substring(0, 3)}
              </text>
            </g>
          );
        })}

        {/* Dynamic Aspect Lines (Harmonious vs Challenging connections) */}
        {planets.map((p1, idx) => {
          return planets.slice(idx + 1).map((p2) => {
            const pos1 = placementsData[p1];
            const pos2 = placementsData[p2];

            const idx1 = SIGN_ORDER.indexOf(pos1.sign);
            const idx2 = SIGN_ORDER.indexOf(pos2.sign);

            if (idx1 === -1 || idx2 === -1) return null;

            const angle1 = (idx1 * 30 + pos1.degree) * (Math.PI / 180);
            const angle2 = (idx2 * 30 + pos2.degree) * (Math.PI / 180);

            const diff = Math.abs((idx1 * 30 + pos1.degree) - (idx2 * 30 + pos2.degree)) % 360;
            const diffNorm = diff > 180 ? 360 - diff : diff;

            // Harmonious aspects: Trine (120°), Sextile (60°)
            // Challenging aspects: Opposition (180°), Square (90°)
            let strokeColor = "";
            if (Math.abs(diffNorm - 120) < 6 || Math.abs(diffNorm - 60) < 4) {
              strokeColor = "var(--accent-sage)"; // Harmonious
            } else if (Math.abs(diffNorm - 180) < 8 || Math.abs(diffNorm - 90) < 6) {
              strokeColor = "var(--accent-terracotta)"; // Challenging
            }

            if (!strokeColor) return null;

            const c1 = getCoordinates(angle1, r - 90);
            const c2 = getCoordinates(angle2, r - 90);

            return (
              <line
                key={`${p1}-${p2}`}
                x1={c1.x}
                y1={c1.y}
                x2={c2.x}
                y2={c2.y}
                stroke={strokeColor}
                strokeWidth="1.2"
                opacity="0.45"
              />
            );
          });
        })}

        {/* Planet Glyphs */}
        {planets.map((planet) => {
          const placementVal = placementsData[planet];
          const signIndex = SIGN_ORDER.indexOf(placementVal.sign);
          if (signIndex === -1) return null;

          const angle = (signIndex * 30 + placementVal.degree) * (Math.PI / 180);
          const c = getCoordinates(angle, r - 60);
          const meta = PLANET_META[planet];

          return (
            <g key={planet}>
              <circle cx={c.x} cy={c.y} r="10" fill="var(--bg-secondary)" stroke={meta.color} strokeWidth="1" />
              <text
                x={c.x}
                y={c.y + 3.5}
                fill="var(--text-primary)"
                fontSize="9"
                fontWeight="bold"
                textAnchor="middle"
                fontFamily="var(--font-sans)"
              >
                {meta.label}
              </text>
            </g>
          );
        })}
      </svg>
    );
  };

  const renderVedicChart = (placementsData: Placements) => {
    const size = 320;

    // Vedic North Indian Diamond Chart Layout:
    // Outer square, diagonals, inner diamonds.
    // 12 Triangular houses.
    // Map planets to houses based on placement values.
    const housePlanets: { [house: number]: string[] } = {};
    for (let h = 1; h <= 12; h++) housePlanets[h] = [];

    Object.entries(placementsData).forEach(([planet, val]) => {
      const meta = PLANET_META[planet];
      if (meta && val.house >= 1 && val.house <= 12) {
        housePlanets[val.house].push(meta.label);
      }
    });

    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="chart-svg">
        {/* Outer square border */}
        <rect x="10" y="10" width="300" height="300" fill="#1b1b17" stroke="var(--border-color)" strokeWidth="2.5" />

        {/* Diagonals */}
        <line x1="10" y1="10" x2="310" y2="310" stroke="var(--border-color)" strokeWidth="1.5" />
        <line x1="10" y1="310" x2="310" y2="10" stroke="var(--border-color)" strokeWidth="1.5" />

        {/* Inner Diamond */}
        <polygon points="160,10 310,160 160,310 10,160" fill="none" stroke="var(--border-color)" strokeWidth="1.5" />

        {/* House Content Renderings (Approximate Positions in Triangle Centers) */}
        {[
          { house: 1, x: 160, y: 70 },
          { house: 2, x: 100, y: 40 },
          { house: 3, x: 50, y: 90 },
          { house: 4, x: 100, y: 160 },
          { house: 5, x: 50, y: 230 },
          { house: 6, x: 100, y: 280 },
          { house: 7, x: 160, y: 250 },
          { house: 8, x: 220, y: 280 },
          { house: 9, x: 270, y: 230 },
          { house: 10, x: 220, y: 160 },
          { house: 11, x: 270, y: 90 },
          { house: 12, x: 220, y: 40 }
        ].map(({ house, x, y }) => (
          <g key={house}>
            {/* House Number badge */}
            <text x={x} y={y - 12} fill="var(--accent-gold)" fontSize="8" fontWeight="600" textAnchor="middle">
              {house}
            </text>
            {/* Planets grouped in the house */}
            <text x={x} y={y + 6} fill="var(--text-primary)" fontSize="10" fontWeight="bold" textAnchor="middle">
              {housePlanets[house].join(" ")}
            </text>
          </g>
        ))}
      </svg>
    );
  };

  return (
    <div className={styles.container}>
      <div className={styles.topGradientBorder}></div>

      {/* Header */}
      <header className={styles.header}>
        <div className={styles.logoArea}>
          <Compass className={styles.logoIcon} />
          <div className={styles.logoText}>
            <h1>AURA ASTROLOGY</h1>
            <p>Humanized Celestial Intelligence</p>
          </div>
        </div>

        <nav className={styles.navMenu}>
          <button
            className={`${styles.navBtn} ${activeTab === "dashboard" ? styles.navBtnActive : ""}`}
            onClick={() => setActiveTab("dashboard")}
          >
            <Calendar size={16} /> Dashboard
          </button>
          <button
            className={`${styles.navBtn} ${activeTab === "chart-calc" ? styles.navBtnActive : ""}`}
            onClick={() => setActiveTab("chart-calc")}
          >
            <Compass size={16} /> Calculate
          </button>
          <button
            className={`${styles.navBtn} ${activeTab === "upload" ? styles.navBtnActive : ""}`}
            onClick={() => setActiveTab("upload")}
          >
            <FileText size={16} /> OCR Document
          </button>
          <button
            className={`${styles.navBtn} ${activeTab === "chat" ? styles.navBtnActive : ""}`}
            onClick={() => setActiveTab("chat")}
          >
            <MessageSquare size={16} /> Astro Chat
          </button>
          <button
            className={`${styles.navBtn} ${activeTab === "settings" ? styles.navBtnActive : ""}`}
            onClick={() => setActiveTab("settings")}
          >
            <Sliders size={16} /> Profile
          </button>
        </nav>

        <div className={styles.authStatusBar}>
          {token ? (
            <button className={styles.authBtn} onClick={handleLogout}>
              <LogOut size={14} /> Log Out
            </button>
          ) : (
            <button className={styles.authBtn} onClick={() => { setAuthMode("login"); setShowAuthModal(true); }}>
              <UserIcon size={14} /> Login / Register
            </button>
          )}
        </div>
      </header>

      {/* Toast Notifications */}
      <div className={styles.toastContainer}>
        {toasts.map((toast) => (
          <div key={toast.id} className={`${styles.toast} ${toast.type === "error" ? styles.toastError : styles.toastSuccess}`}>
            {toast.message}
          </div>
        ))}
      </div>

      {/* Main Area */}
      <main className={styles.main}>

        {/* --- Tab 1: Dashboard --- */}
        {activeTab === "dashboard" && (
          <section>
            <div className={styles.dashboardHero}>
              <div>
                <h2>Your Celestial Blueprint</h2>
                <p>View active transits, placements, and lifecyle predictions.</p>
              </div>
              <div className={styles.systemSelector}>
                <label>Astrology System</label>
                <select
                  value={calculationSystem}
                  onChange={(e) => setCalculationSystem(e.target.value as "Western" | "Vedic")}
                >
                  <option value="Western">Western Tropical</option>
                  <option value="Vedic">Vedic Sidereal</option>
                </select>
              </div>
            </div>

            <div className={styles.dashboardGrid}>

              {/* Left: Chart Visualizer */}
              <div className={styles.gridCard}>
                <div className={styles.cardHeader}>
                  <h3>Natal Chart Alignment</h3>
                  <span className={styles.badge}>{calculationSystem}</span>
                </div>
                <div className={styles.chartCanvasContainer}>
                  <div className={styles.chartRenderingTarget}>
                    {placements ? (
                      calculationSystem === "Western" ? renderWesternChart(placements) : renderVedicChart(placements)
                    ) : (
                      <div className={styles.emptyStateMessage}>
                        <Compass size={40} />
                        <p>Calculate your custom chart alignment blueprint to activate the visualization rendering engine.</p>
                        <button className={styles.accentBtn} onClick={() => setActiveTab("chart-calc")}>
                          Enter Birth Data
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Right: Timeline Forecast */}
              <div className={styles.gridCard}>
                <div className={styles.cardHeader}>
                  <h3>Astrological Forecast Timeline</h3>
                  <div className={styles.timeframeSelector}>
                    <button
                      className={`${styles.timeframeBtn} ${forecastTimeframe === "weekly" ? styles.timeframeBtnActive : ""}`}
                      onClick={() => setForecastTimeframe("weekly")}
                    >
                      Weekly
                    </button>
                    <button
                      className={`${styles.timeframeBtn} ${forecastTimeframe === "monthly" ? styles.timeframeBtnActive : ""}`}
                      onClick={() => setForecastTimeframe("monthly")}
                    >
                      Monthly
                    </button>
                  </div>
                </div>

                <div className={styles.forecastContainer}>
                  {timeline && timeline.intervals.length > 0 ? (
                    timeline.intervals.map((interval, i) => (
                      <div key={i} className={styles.intervalItem}>
                        <div className={styles.intervalHeader}>
                          <span className={styles.intervalLabel}>Period Interval {i + 1}</span>
                          <span className={styles.intervalDates}>
                            {interval.start_date} to {interval.end_date}
                          </span>
                        </div>
                        <div className={styles.domainSummaryGrid}>
                          {(() => {
                            const domainGroups: { [domain: string]: { maxStrength: number; count: number } } = {};
                            interval.active_signals.forEach((sig) => {
                              const d = sig.domain ? sig.domain.toUpperCase() : "GENERAL";
                              if (!domainGroups[d]) {
                                domainGroups[d] = { maxStrength: sig.strength, count: 1 };
                              } else {
                                domainGroups[d].count += 1;
                                if (sig.strength > domainGroups[d].maxStrength) {
                                  domainGroups[d].maxStrength = sig.strength;
                                }
                              }
                            });

                            return Object.entries(domainGroups).map(([domain, data]) => {
                              const meta = DOMAIN_MAP[domain] || {
                                label: domain.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()),
                                color: "var(--accent-gold)"
                              };
                              const percent = Math.round(data.maxStrength * 100);
                              return (
                                <div key={domain} className={styles.domainCard}>
                                  <div className={styles.domainCardHeader}>
                                    <span className={styles.domainTitle}>{meta.label}</span>
                                    <span className={styles.domainPercent}>{percent}% Alignment</span>
                                  </div>
                                  <div className={styles.strengthTrack}>
                                    <div
                                      className={styles.strengthBar}
                                      style={{ width: `${percent}%`, backgroundColor: meta.color }}
                                    ></div>
                                  </div>
                                </div>
                              );
                            });
                          })()}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className={styles.emptyStateMessage}>
                      <Calendar size={40} />
                      <p>Generate predictions by calculating your chart blueprint above.</p>
                    </div>
                  )}
                </div>
              </div>

            </div>

            {/* Lifecycle Scenarios */}
            <div className={styles.scenariosRowHeader}>
              <h3>Structured Lifecycle Scenarios</h3>
              <p>Deterministically generated scenarios using system correlation metrics.</p>
            </div>

            <div className={styles.scenariosGrid}>
              {scenarios.length > 0 ? (
                scenarios.map((scen, idx) => (
                  <div key={scen.scenario_id} className={styles.gridCard}>
                    <div className={styles.scenarioItemHeader}>
                      <h4>{idx === 0 ? "Primary Alignment" : idx === 1 ? "Alternative Shift" : "Challenging Matrix"}</h4>
                      <span className={styles.badge}>
                        {typeof scen.uncertainty === "object" && scen.uncertainty !== null
                          ? (scen.uncertainty.uncertainty_level || "Medium Confidence")
                          : String(scen.uncertainty || "Medium Confidence")}
                      </span>
                    </div>
                    <div className={styles.scenarioItemBody}>
                      <p style={{ marginBottom: "14px", fontStyle: "italic" }}>
                        Domain: {scen.domain} | Support score: {scen.support_score.toFixed(2)}
                      </p>
                      <div className={styles.evidenceList}>
                        {scen.evidence.map((ev, i) => (
                          <div key={i} className={styles.evidenceItem}>
                            <Workflow size={12} />
                            <span>{ev}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <>
                  <div className={`${styles.gridCard} ${styles.scenarioItem}`}>
                    <h4>Primary Path</h4>
                    <p>No active forecast computed.</p>
                  </div>
                  <div className={`${styles.gridCard} ${styles.scenarioItem}`}>
                    <h4>Alternative Path</h4>
                    <p>No active forecast computed.</p>
                  </div>
                  <div className={`${styles.gridCard} ${styles.scenarioItem}`}>
                    <h4>Challenge Scenario</h4>
                    <p>No active forecast computed.</p>
                  </div>
                </>
              )}
            </div>

          </section>
        )}

        {/* --- Tab 2: Chart Calc --- */}
        {activeTab === "chart-calc" && (
          <section className={styles.splitView}>
            <div className={styles.formContainerCard}>
              <h2>Calculate Natal Chart</h2>
              <p className={styles.formDesc}>Provide coordinates and birth specifics below to map astrological coordinates.</p>

              <form onSubmit={handleCalculateChart} className={styles.astroForm}>
                <div className={styles.formGroupRow}>
                  <div className={styles.formGroup}>
                    <label>Date of Birth</label>
                    <input
                      type="date"
                      value={birthDate}
                      onChange={(e) => setBirthDate(e.target.value)}
                      required
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label>Exact Birth Time</label>
                    <input
                      type="time"
                      value={birthTime}
                      onChange={(e) => setBirthTime(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className={styles.formGroup}>
                  <label>Birth Place (City, Country)</label>
                  <input
                    type="text"
                    value={birthPlace}
                    onChange={(e) => setBirthPlace(e.target.value)}
                    placeholder="e.g. New York, NY"
                    required
                  />
                </div>

                <div className={styles.formGroupRow}>
                  <div className={styles.formGroup}>
                    <label>Latitude</label>
                    <input
                      type="number"
                      step="any"
                      min="-90"
                      max="90"
                      value={birthLat}
                      onChange={(e) => setBirthLat(e.target.value)}
                      required
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label>Longitude</label>
                    <input
                      type="number"
                      step="any"
                      min="-180"
                      max="180"
                      value={birthLon}
                      onChange={(e) => setBirthLon(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className={styles.formGroupRow}>
                  <div className={styles.formGroup}>
                    <label>Timezone (IANA)</label>
                    <input
                      type="text"
                      value={birthTz}
                      onChange={(e) => setBirthTz(e.target.value)}
                      placeholder="e.g. America/New_York"
                      required
                    />
                  </div>
                  <div className={`${styles.formGroup} ${styles.dstCheckboxGroup}`}>
                    <input
                      type="checkbox"
                      id="dst-check"
                      checked={birthDst}
                      onChange={(e) => setBirthDst(e.target.checked)}
                    />
                    <label htmlFor="dst-check" className={styles.inlineLabel}>Daylight Saving Time</label>
                  </div>
                </div>

                <div className={styles.formActions}>
                  <button type="submit" className="btn-primary" disabled={isCalculating}>
                    {isCalculating ? (
                      <>
                        <Loader2 className="animate-spin inline-block mr-2" size={16} /> Calculating...
                      </>
                    ) : "Calculate Chart Blueprint"}
                  </button>
                </div>
              </form>
            </div>

            <div className={styles.infoSidebarCard}>
              <h3>Astronomical Precision</h3>
              <p>Our algorithms access Swiss Ephemeris data files, translating raw planetary orbits into tropical/sidereal signs & houses.</p>
              <div className={styles.featuresList}>
                <div className={styles.featureItem}>
                  <Compass />
                  <div>
                    <h5>Multiple House Projections</h5>
                    <p>Calculates exact planetary degrees, house boundaries, and aspect configurations.</p>
                  </div>
                </div>
                <div className={styles.featureItem}>
                  <Workflow />
                  <div>
                    <h5>Temporal Normalization</h5>
                    <p>Translates localized timelines into astronomical Ephemeris UTC values.</p>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* --- Tab 3: OCR Upload --- */}
        {activeTab === "upload" && (
          <section className={styles.splitView}>
            <div className={styles.formContainerCard}>
              <h2>Image OCR Analysis</h2>
              <p className={styles.formDesc}>Upload scanned birth documents, charts, or diagrams. Our layout parser will identify text coordinates and reconstruct factors.</p>

              <div
                className={styles.uploadDropzone}
                onClick={() => document.getElementById("file-file")?.click()}
              >
                <Upload className={styles.uploadIcon} />
                <p className={styles.dropzoneText}>
                  Drag files here or <span className={styles.browseLink}>browse from computer</span>
                </p>
                <input
                  type="file"
                  id="file-file"
                  accept="image/*,application/pdf"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleFileUpload(e.target.files[0]);
                    }
                  }}
                />
              </div>

              {isUploading && (
                <div className={styles.progressContainer}>
                  <div className={styles.progressBar}>
                    <div className={styles.progressFill} style={{ width: `${ocrProgress}%` }}></div>
                  </div>
                  <p>Processing alignment layers... ({ocrProgress}%)</p>
                </div>
              )}

              {ocrResults && (
                <div className={styles.ocrResults}>
                  <h4>Extracted Chart Representation</h4>
                  <pre className={styles.resultsCode}>{ocrResults}</pre>
                </div>
              )}
            </div>

            <div className={styles.infoSidebarCard}>
              <h3>Pipeline Extraction Architecture</h3>
              <p>Processes raw uploads, runs layout classification blocks, runs text OCR engines, and translates visual factors into structured placements.</p>
            </div>
          </section>
        )}

        {/* --- Tab 4: Chat --- */}
        {activeTab === "chat" && (
          <section className={styles.chatLayout}>
            {/* Chat Sidebar */}
            <div className={styles.chatSidebar}>
              <div className={styles.sidebarHeader}>
                <h3>Conversations</h3>
                <button className={styles.newChatBtn} onClick={handleStartNewChat}>
                  <Plus size={14} /> New
                </button>
              </div>
              <div className={styles.conversationsList}>
                {conversations.map((conv) => (
                  <button
                    key={conv.conversation_id}
                    className={`${styles.convItem} ${currentConversationId === conv.conversation_id ? styles.convItemActive : ""}`}
                    onClick={() => {
                      setCurrentConversationId(conv.conversation_id);
                      if (conv.messages && conv.messages.length > 0) {
                        setMessages(
                          conv.messages.map((m: any) => ({
                            sender: m.role === "user" ? "user" : "assistant",
                            text: m.content,
                            time: m.timestamp ? new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Just now"
                          }))
                        );
                      } else {
                        setMessages([
                          { sender: "assistant", text: "Welcome to your astrological consultation thread.", time: "Just now" }
                        ]);
                      }
                    }}
                  >
                    <span className={styles.convItemTitle}>{conv.title || "Astrology Consultation"}</span>
                    <span className={styles.convItemMeta}>
                      {conv.updated_at && !isNaN(new Date(conv.updated_at).getTime())
                        ? new Date(conv.updated_at).toLocaleDateString()
                        : conv.created_at && !isNaN(new Date(conv.created_at).getTime())
                          ? new Date(conv.created_at).toLocaleDateString()
                          : "Active Session"}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Chat Window */}
            <div className={styles.chatWindow}>
              <div className={styles.chatHeader}>
                <div className={styles.activeChatInfo}>
                  <h4>AstroConsultant Agent</h4>
                  <p className={styles.activeStatus}>Knowledge-Retrieval Augmented RAG</p>
                </div>
              </div>

              <div className={styles.chatMessages} ref={chatContainerRef} onScroll={handleChatScroll}>
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className={`${styles.message} ${msg.sender === "user" ? styles.userMsg : styles.assistantMsg}`}
                  >
                    <div className={styles.messageBubble}>{msg.text}</div>
                    <span className={styles.messageTime}>{msg.time}</span>
                  </div>
                ))}
                {isSendingMessage && (
                  <div className={`${styles.message} ${styles.assistantMsg}`}>
                    <div className={styles.messageBubble}>
                      <Loader2 className="animate-spin inline-block" size={16} /> Consultative synthesis active...
                    </div>
                  </div>
                )}
                <div ref={chatBottomRef}></div>
              </div>

              {showScrollBottom && (
                <button
                  type="button"
                  className={styles.scrollDownBtn}
                  onClick={scrollToBottom}
                  title="Scroll to bottom"
                >
                  <ChevronDown size={18} />
                  <span>Scroll down</span>
                </button>
              )}

              <form onSubmit={handleSendMessage} className={styles.chatInputBar}>
                <input
                  type="text"
                  value={chatMessageInput}
                  onChange={(e) => setChatMessageInput(e.target.value)}
                  placeholder="Ask about lifecycle transits, specific chart placements, or Vedic yogas..."
                  required
                />
                <button type="submit" className={styles.chatSendBtn}>
                  <Send size={16} />
                </button>
              </form>
            </div>
          </section>
        )}

        {/* --- Tab 5: Settings --- */}
        {activeTab === "settings" && (
          <section className={styles.splitView}>
            <div className={styles.formContainerCard}>
              <h2>Astrological Profile</h2>
              <p className={styles.formDesc}>Configure your name parameters and synchronize birth properties.</p>

              <form onSubmit={handleUpdateProfile} className={styles.astroForm}>
                <div className={styles.formGroupRow}>
                  <div className={styles.formGroup}>
                    <label>First Name</label>
                    <input
                      type="text"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label>Last Name</label>
                    <input
                      type="text"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                    />
                  </div>
                </div>

                <div className={styles.formGroup}>
                  <label>Current Location</label>
                  <input
                    type="text"
                    value={currentLocation}
                    onChange={(e) => setCurrentLocation(e.target.value)}
                  />
                </div>

                <div className={styles.formActions}>
                  <button type="submit" className="btn-primary">
                    Save Profile Settings
                  </button>
                </div>
              </form>

              <div style={{ margin: "24px 0", borderBottom: "1px solid var(--border-color)" }}></div>

              <h3>Current Coordinates Mapping</h3>
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "8px" }}>
                Active reference birth data: {birthPlace} (Lat: {birthLat}, Lon: {birthLon}, Tz: {birthTz}).
              </p>
            </div>

            <div className={styles.infoSidebarCard}>
              <h3>Human-Centric Data Policy</h3>
              <p>Your coordinates data is strictly verified dynamically on Swiss Ephemeris. We do not persist raw coordinates for marketing analysis.</p>
            </div>
          </section>
        )}

      </main>

      {/* Star Feedback Button */}
      <button className={styles.feedbackFab} onClick={() => setShowFeedbackModal(true)}>
        <Star size={16} /> Feedback
      </button>

      {/* --- Feedback Modal --- */}
      {showFeedbackModal && (
        <div className={styles.modalBackdrop}>
          <div className={styles.modalCard}>
            <div className={styles.modalHeader}>
              <h3>Submit Alignment Feedback</h3>
              <button className={styles.closeModalBtn} onClick={() => setShowFeedbackModal(false)}>
                &times;
              </button>
            </div>

            <form onSubmit={handleFeedbackSubmit} className={styles.astroForm}>
              <div className={styles.formGroup}>
                <label>Feedback Target</label>
                <select
                  value={feedbackItemType}
                  onChange={(e) => setFeedbackItemType(e.target.value)}
                >
                  <option value="prediction">Forecasting Scenario / Prediction</option>
                  <option value="chat_message">Chat Assistant Explanation</option>
                  <option value="chart">Chart Coordinate Accuracy</option>
                </select>
              </div>

              <div className={styles.formGroup}>
                <label>Rate System Accuracy</label>
                <div className={styles.starRatingSelector}>
                  {[5, 4, 3, 2, 1].map((starVal) => (
                    <React.Fragment key={starVal}>
                      <input
                        type="radio"
                        id={`star-${starVal}`}
                        name="rating"
                        value={starVal}
                        checked={feedbackRating === starVal}
                        onChange={() => setFeedbackRating(starVal)}
                      />
                      <label htmlFor={`star-${starVal}`}>
                        <Star size={24} fill={feedbackRating >= starVal ? "var(--accent-gold)" : "none"} />
                      </label>
                    </React.Fragment>
                  ))}
                </div>
              </div>

              <div className={styles.formGroup}>
                <label>Review details</label>
                <textarea
                  value={feedbackComment}
                  onChange={(e) => setFeedbackComment(e.target.value)}
                  placeholder="Share details on calculation match, aspect deviations..."
                  rows={4}
                />
              </div>

              <div className={styles.modalActions}>
                <button type="button" className={styles.cancelBtn} onClick={() => setShowFeedbackModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Submit Feedback
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- Auth Modal --- */}
      {showAuthModal && (
        <div className={styles.modalBackdrop}>
          <div className={styles.modalCard}>
            <div className={styles.modalHeader}>
              <h3>{authMode === "login" ? "Sign In" : "Register"}</h3>
              <button className={styles.closeModalBtn} onClick={() => setShowAuthModal(false)}>
                &times;
              </button>
            </div>

            <form onSubmit={handleAuthSubmit} className={styles.astroForm}>
              <div className={styles.formGroup}>
                <label>Email Address</label>
                <input
                  type="email"
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  placeholder="e.g. user@example.com"
                  required
                />
              </div>
              <div className={styles.formGroup}>
                <label>Password</label>
                <input
                  type="password"
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                />
              </div>

              <div className={styles.authToggle}>
                <p>
                  {authMode === "login" ? "Don't have an account? " : "Already have an account? "}
                  <span
                    className={styles.toggleLink}
                    onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}
                  >
                    {authMode === "login" ? "Register here" : "Login here"}
                  </span>
                </p>
              </div>

              <div className={styles.modalActions}>
                <button type="button" className={styles.cancelBtn} onClick={() => setShowAuthModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  {authMode === "login" ? "Sign In" : "Register"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
