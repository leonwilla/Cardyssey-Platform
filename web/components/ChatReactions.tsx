"use client";

import { useState } from "react";

const EMOJIS = ["❤️", "👍", "🔥", "😂", "😮"] as const;

export type Reaction = {
  emoji: string;
  count: number;
  reactedByMe: boolean;
};

export function ChatReactions({
  reactions,
  onToggle,
}: {
  reactions?: Reaction[];
  onToggle: (emoji: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const active = (reactions ?? []).filter((reaction) => reaction.count > 0);

  function select(emoji: string) {
    onToggle(emoji);
    setExpanded(false);
  }

  return (
    <div className="chatReactions" aria-label="Nachrichtenreaktionen">
      {active.map((reaction) => (
        <button
          type="button"
          key={reaction.emoji}
          className={reaction.reactedByMe ? "chatReactionPill selected" : "chatReactionPill"}
          onClick={() => select(reaction.emoji)}
          aria-label={`${reaction.emoji} Reaktion ${reaction.reactedByMe ? "entfernen" : "hinzufügen"}`}
          aria-pressed={reaction.reactedByMe}
        >
          {reaction.emoji} <span>{reaction.count}</span>
        </button>
      ))}
      <div className="chatReactionPicker">
        <button
          className="chatReactionAdd"
          type="button"
          onClick={() => setExpanded((previous) => !previous)}
          aria-expanded={expanded}
          aria-label="Reaktion auswählen"
          title="Reaktion hinzufügen"
        >
          {expanded ? "×" : "☺"}
        </button>
        {expanded && (
          <div className="chatReactionOptions" role="group" aria-label="Emoji auswählen">
            {EMOJIS.map((emoji) => (
              <button
                type="button"
                key={emoji}
                onClick={() => select(emoji)}
                aria-label={`Mit ${emoji} reagieren`}
              >
                {emoji}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
