import type { ChatMessage as ChatMessageType } from "@/lib/api";

interface ChatMessageProps {
  message: ChatMessageType;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex items-start gap-3 animate-fade-in-up ${
        isUser ? "flex-row-reverse" : ""
      }`}
    >
      {/* Avatar */}
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-primary text-primary-foreground"
        }`}
      >
        {isUser ? "You" : "AI"}
      </div>

      {/* Message bubble */}
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "rounded-tr-sm bg-primary text-primary-foreground"
            : "rounded-tl-sm bg-muted text-foreground"
        }`}
      >
        {/* Render message with basic markdown-like formatting */}
        <MessageContent content={message.content} />

        {/* Timestamp */}
        <p
          className={`mt-1.5 text-[10px] ${
            isUser
              ? "text-primary-foreground/60"
              : "text-muted-foreground/70"
          }`}
        >
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>
    </div>
  );
}

/**
 * Renders message content with basic formatting:
 * - **bold** text
 * - Line breaks
 * - Bullet points (- items)
 */
function MessageContent({ content }: { content: string }) {
  const lines = content.split("\n");

  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        if (!line.trim()) return <br key={i} />;

        // Handle bullet points
        const isBullet = line.trim().startsWith("- ");
        const processedLine = isBullet ? line.trim().slice(2) : line;

        // Handle **bold** text
        const parts = processedLine.split(/(\*\*[^*]+\*\*)/g);
        const rendered = parts.map((part, j) => {
          if (part.startsWith("**") && part.endsWith("**")) {
            return (
              <strong key={j} className="font-semibold">
                {part.slice(2, -2)}
              </strong>
            );
          }
          return <span key={j}>{part}</span>;
        });

        if (isBullet) {
          return (
            <div key={i} className="flex items-start gap-2 pl-1">
              <span className="mt-1.5 h-1 w-1 rounded-full bg-current opacity-60 shrink-0" />
              <span>{rendered}</span>
            </div>
          );
        }

        return <p key={i}>{rendered}</p>;
      })}
    </div>
  );
}
