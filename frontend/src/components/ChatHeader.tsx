import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface ChatHeaderProps {
  isDark: boolean;
  onToggleTheme: () => void;
}

export default function ChatHeader({ isDark, onToggleTheme }: ChatHeaderProps) {
  return (
    <div className="flex items-center justify-between px-5 py-4 border-b">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-sm">
          AS
        </div>
        <div>
          <h1 className="text-base font-semibold tracking-tight">AutoStream</h1>
          <p className="text-xs text-muted-foreground">
            Social-to-Lead AI Agent
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Badge variant="secondary" className="gap-1.5 text-xs font-medium">
          <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse-online" />
          AI Agent
        </Badge>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onToggleTheme}
          aria-label="Toggle theme"
          id="theme-toggle"
        >
          {isDark ? (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2" />
              <path d="M12 20v2" />
              <path d="m4.93 4.93 1.41 1.41" />
              <path d="m17.66 17.66 1.41 1.41" />
              <path d="M2 12h2" />
              <path d="M20 12h2" />
              <path d="m6.34 17.66-1.41 1.41" />
              <path d="m19.07 4.93-1.41 1.41" />
            </svg>
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
            </svg>
          )}
        </Button>
      </div>
    </div>
  );
}
