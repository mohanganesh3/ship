/**
 * Custom SVG Icon Set for Maritime AI
 * 
 * Each icon: 24×24 default viewBox, stroke-width 1.5
 * Accepts: size (number), color (string)
 * 
 * NO ICON LIBRARIES. Every path is hand-crafted.
 */
import React from 'react';
import Svg, { Path, Circle, Line, Polyline, Rect, G } from 'react-native-svg';

interface IconProps {
  size?: number;
  color?: string;
}

// ─── ANCHOR ──────────────────────────────────────────────────
export function AnchorIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Circle cx="12" cy="5" r="3" />
      <Line x1="12" y1="8" x2="12" y2="22" />
      <Path d="M5 12H2a10 10 0 0 0 20 0h-3" />
    </Svg>
  );
}

// ─── ENGINE BLOCK ────────────────────────────────────────────
export function EngineBlockIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Rect x="4" y="6" width="16" height="12" rx="2" />
      <Path d="M8 6V4M16 6V4" />
      <Path d="M4 12h16" />
      <Path d="M9 15h2M13 15h2" />
      <Path d="M9 9h2M13 9h2" />
      <Path d="M2 10v4M22 10v4" />
    </Svg>
  );
}

// ─── LIFEBUOY ────────────────────────────────────────────────
export function LifebuoyIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Circle cx="12" cy="12" r="10" />
      <Circle cx="12" cy="12" r="4" />
      <Line x1="4.93" y1="4.93" x2="9.17" y2="9.17" />
      <Line x1="14.83" y1="14.83" x2="19.07" y2="19.07" />
      <Line x1="14.83" y1="9.17" x2="19.07" y2="4.93" />
      <Line x1="4.93" y1="19.07" x2="9.17" y2="14.83" />
    </Svg>
  );
}

// ─── GEAR ────────────────────────────────────────────────────
export function GearIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Circle cx="12" cy="12" r="3" />
      <Path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </Svg>
  );
}

// ─── COMPASS ─────────────────────────────────────────────────
export function CompassIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Circle cx="12" cy="12" r="10" />
      <Path d="M16.24 7.76l-2.12 6.36-6.36 2.12 2.12-6.36 6.36-2.12z" fill={color} fillOpacity={0.15} />
    </Svg>
  );
}

// ─── SEND ARROW ──────────────────────────────────────────────
export function SendArrowIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Path d="M22 2L11 13" />
      <Path d="M22 2L15 22L11 13L2 9L22 2Z" />
    </Svg>
  );
}

// ─── MICROPHONE ──────────────────────────────────────────────
export function MicrophoneIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Rect x="9" y="2" width="6" height="11" rx="3" />
      <Path d="M19 10v1a7 7 0 0 1-14 0v-1" />
      <Line x1="12" y1="18" x2="12" y2="22" />
      <Line x1="8" y1="22" x2="16" y2="22" />
    </Svg>
  );
}

// ─── CHEVRON LEFT ────────────────────────────────────────────
export function ChevronLeftIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Polyline points="15 18 9 12 15 6" />
    </Svg>
  );
}

// ─── SEARCH ──────────────────────────────────────────────────
export function SearchIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Circle cx="11" cy="11" r="8" />
      <Line x1="21" y1="21" x2="16.65" y2="16.65" />
    </Svg>
  );
}

// ─── PIN ─────────────────────────────────────────────────────
export function PinIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Path d="M12 17v5" />
      <Path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76z" />
    </Svg>
  );
}

// ─── TRASH ───────────────────────────────────────────────────
export function TrashIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Polyline points="3 6 5 6 21 6" />
      <Path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <Line x1="10" y1="11" x2="10" y2="17" />
      <Line x1="14" y1="11" x2="14" y2="17" />
    </Svg>
  );
}

// ─── COPY ────────────────────────────────────────────────────
export function CopyIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Rect x="9" y="9" width="13" height="13" rx="2" />
      <Path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </Svg>
  );
}

// ─── REFRESH ─────────────────────────────────────────────────
export function RefreshIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Polyline points="23 4 23 10 17 10" />
      <Path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
    </Svg>
  );
}

// ─── BRAIN (thinking mode) ───────────────────────────────────
export function BrainIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Path d="M12 2a4 4 0 0 1 4 4c0 1.1-.45 2.1-1.17 2.83A5 5 0 0 1 17 13.5c0 1.38-.56 2.63-1.46 3.54A4.5 4.5 0 0 1 12 22" />
      <Path d="M12 2a4 4 0 0 0-4 4c0 1.1.45 2.1 1.17 2.83A5 5 0 0 0 7 13.5c0 1.38.56 2.63 1.46 3.54A4.5 4.5 0 0 0 12 22" />
      <Line x1="12" y1="2" x2="12" y2="22" />
      <Path d="M8 8h2M14 8h2" />
      <Path d="M7.5 14h3M13.5 14h3" />
    </Svg>
  );
}

// ─── ALERT CIRCLE ────────────────────────────────────────────
export function AlertCircleIcon({ size = 24, color = '#C44D3F' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Circle cx="12" cy="12" r="10" />
      <Line x1="12" y1="8" x2="12" y2="12" />
      <Line x1="12" y1="16" x2="12.01" y2="16" />
    </Svg>
  );
}

// ─── CHAT ────────────────────────────────────────────────────
export function ChatIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </Svg>
  );
}

// ─── PLUS CIRCLE ─────────────────────────────────────────────
export function PlusCircleIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Circle cx="12" cy="12" r="10" />
      <Line x1="12" y1="8" x2="12" y2="16" />
      <Line x1="8" y1="12" x2="16" y2="12" />
    </Svg>
  );
}

// ─── THUMBS UP ───────────────────────────────────────────────
export function ThumbsUpIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Path d="M14 9V5a3 3 0 0 0-6 0v1.7" />
      <Path d="M4 14h2a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H4a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1z" />
      <Path d="M10 12h6.5a2.5 2.5 0 0 1 0 5H15l1.3 2.6a1.5 1.5 0 0 1-1.3 2.4h-2.5a2 2 0 0 1-1.7-1l-1.8-3" />
    </Svg>
  );
}

// ─── WAVE (decorative) ───────────────────────────────────────
export function WaveIcon({ size = 24, color = '#B4B4A9' }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <Path d="M2 12c2-3 4-3 6 0s4 3 6 0 4-3 6 0" />
      <Path d="M2 17c2-3 4-3 6 0s4 3 6 0 4-3 6 0" />
    </Svg>
  );
}


