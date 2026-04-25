/**
 * MarkdownRenderer — native markdown parsing for AI response text.
 *
 * Supports: **bold**, *italic*, `code`, ```blocks```, headings, lists, tables.
 * No WebView — uses native Text and View components only.
 *
 * Fix: paragraphs preserve line breaks (join with '\n' not ' ') so numbered
 * maritime procedures render as separate lines rather than one run-on sentence.
 */
import React, { useMemo } from 'react';
import { Text, View, StyleSheet } from 'react-native';
import { Fonts, Type, Colors, Space, Radius } from '../constants/theme';
import { useTheme } from '../providers/ThemeProvider';

interface MarkdownRendererProps {
  content: string;
  color?: string;
}

export const MarkdownRenderer = React.memo(function MarkdownRenderer({
  content,
  color,
}: MarkdownRendererProps) {
  const { colors, isDark } = useTheme();
  const textColor = color || colors.text1;
  const blocks = useMemo(() => parseBlocks(content), [content]);

  return (
    <View>
      {blocks.map((block, i) => {
        if (block.type === 'code') {
          return (
            <View
              key={i}
              style={[styles.codeBlock, { backgroundColor: isDark ? Colors.bg0 : Colors.lightBg3 }]}
            >
              <Text style={[styles.codeText, { color: textColor }]}>{block.text}</Text>
            </View>
          );
        }
        if (block.type === 'table') {
          return (
            <View key={i} style={[styles.tableContainer, { borderColor: colors.borderSubtle }]}>
              {block.text.split('\n').filter(l => !l.includes('|-')).map((row, ri) => (
                <View
                  key={ri}
                  style={[
                    styles.tableRow,
                    ri === 0 && { backgroundColor: isDark ? Colors.bg2 : Colors.lightBg3 },
                  ]}
                >
                  {row.split('|').filter(c => c.trim() !== '').map((cell, ci) => (
                    <Text
                      key={ci}
                      style={[
                        styles.tableCell,
                        { color: textColor },
                        ri === 0 && { fontFamily: Fonts.bodySemibold },
                      ]}
                    >
                      {cell.trim()}
                    </Text>
                  ))}
                </View>
              ))}
            </View>
          );
        }
        if (block.type === 'heading') {
          return (
            <Text
              key={i}
              style={[styles.heading, { color: textColor, marginTop: i > 0 ? Space.lg : 0 }]}
            >
              {block.text}
            </Text>
          );
        }
        if (block.type === 'listItem') {
          return (
            <View key={i} style={styles.listItem}>
              <Text style={[styles.bullet, { color: colors.text3 }]}>
                {block.ordered ? `${block.number}.` : '•'}
              </Text>
              <Text style={[styles.bodyText, { color: textColor, flex: 1 }]}>
                {renderInline(block.text, textColor, isDark)}
              </Text>
            </View>
          );
        }
        // Paragraph / spacer
        if (!block.text.trim()) {
          return <View key={i} style={{ height: Space.sm }} />;
        }
        return (
          <Text key={i} style={[styles.bodyText, { color: textColor, marginBottom: Space.sm }]}>
            {renderInline(block.text, textColor, isDark)}
          </Text>
        );
      })}
    </View>
  );
});

function renderInline(text: string, color: string, isDark: boolean): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(<Text key={`t-${lastIndex}`}>{text.slice(lastIndex, match.index)}</Text>);
    }
    if (match[2]) {
      parts.push(
        <Text key={`b-${match.index}`} style={{ fontFamily: Fonts.bodySemibold }}>{match[2]}</Text>,
      );
    } else if (match[3]) {
      parts.push(
        <Text key={`i-${match.index}`} style={{ fontStyle: 'italic' }}>{match[3]}</Text>,
      );
    } else if (match[4]) {
      parts.push(
        <Text
          key={`c-${match.index}`}
          style={{
            fontFamily: Fonts.mono,
            fontSize: 14,
            backgroundColor: isDark ? Colors.bg0 : Colors.lightBg3,
            paddingHorizontal: 4,
            borderRadius: 3,
          }}
        >
          {match[4]}
        </Text>,
      );
    }
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push(<Text key={`t-${lastIndex}`}>{text.slice(lastIndex)}</Text>);
  }
  return parts.length > 0 ? parts : [<Text key="0">{text}</Text>];
}

interface Block {
  type: 'paragraph' | 'code' | 'heading' | 'listItem' | 'table';
  text: string;
  ordered?: boolean;
  number?: number;
}

function parseBlocks(content: string): Block[] {
  const lines = content.split('\n');
  const blocks: Block[] = [];
  let inCode = false;
  let codeBuffer: string[] = [];
  let paragraphLines: string[] = [];

  const flushParagraph = () => {
    if (paragraphLines.length === 0) return;
    // Join with '\n' to preserve line breaks within a paragraph —
    // critical for maritime procedures that read as one prose block.
    const text = paragraphLines.join('\n').trim();
    if (text) blocks.push({ type: 'paragraph', text });
    paragraphLines = [];
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // ── Code blocks ──────────────────────────────────────────────────────
    if (line.startsWith('```')) {
      flushParagraph();
      if (inCode) {
        blocks.push({ type: 'code', text: codeBuffer.join('\n') });
        codeBuffer = [];
        inCode = false;
      } else {
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      codeBuffer.push(line);
      continue;
    }

    // ── Tables ───────────────────────────────────────────────────────────
    if (line.trim().startsWith('|') && lines[i + 1]?.trim().includes('|-')) {
      flushParagraph();
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        tableLines.push(lines[i]);
        i++;
      }
      i--; // compensate for outer loop increment
      blocks.push({ type: 'table', text: tableLines.join('\n') });
      continue;
    }

    // ── Headings ─────────────────────────────────────────────────────────
    const headingMatch = line.match(/^(#{1,3})\s+(.+)/);
    if (headingMatch) {
      flushParagraph();
      blocks.push({ type: 'heading', text: headingMatch[2] });
      continue;
    }

    // ── List items ───────────────────────────────────────────────────────
    const ulMatch = line.match(/^[\s]*[-*]\s+(.+)/);
    const olMatch = line.match(/^[\s]*(\d+)\.\s+(.+)/);
    if (ulMatch) {
      flushParagraph();
      blocks.push({ type: 'listItem', text: ulMatch[1] });
      continue;
    }
    if (olMatch) {
      flushParagraph();
      blocks.push({ type: 'listItem', text: olMatch[2], ordered: true, number: parseInt(olMatch[1], 10) });
      continue;
    }

    // ── Blank line → flush current paragraph ─────────────────────────────
    if (line.trim() === '') {
      flushParagraph();
      continue;
    }

    // ── Regular paragraph line ───────────────────────────────────────────
    paragraphLines.push(line);
  }

  flushParagraph();
  if (inCode && codeBuffer.length) {
    blocks.push({ type: 'code', text: codeBuffer.join('\n') });
  }

  return blocks;
}

const styles = StyleSheet.create({
  bodyText: {
    fontFamily: Fonts.body,
    fontSize: Type.base.fontSize,
    lineHeight: Type.base.lineHeight,
  },
  heading: {
    fontFamily: Fonts.bodySemibold,
    fontSize: Type.md.fontSize,
    lineHeight: Type.md.lineHeight,
    marginBottom: Space.xs,
  },
  codeBlock: {
    borderRadius: Radius.sm,
    padding: Space.md,
    marginVertical: Space.sm,
  },
  codeText: {
    fontFamily: Fonts.mono,
    fontSize: 13.5,
    lineHeight: 20,
  },
  listItem: {
    flexDirection: 'row',
    gap: Space.sm,
    marginBottom: Space.xs,
    paddingLeft: Space.xs,
  },
  bullet: {
    fontFamily: Fonts.body,
    fontSize: Type.base.fontSize,
    lineHeight: Type.base.lineHeight,
    width: 16,
  },
  tableContainer: {
    borderWidth: 1,
    borderRadius: Radius.sm,
    marginVertical: Space.sm,
    overflow: 'hidden',
  },
  tableRow: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.05)',
  },
  tableCell: {
    flex: 1,
    padding: Space.xs,
    fontSize: 13,
    borderRightWidth: 1,
    borderRightColor: 'rgba(0,0,0,0.05)',
  },
});
