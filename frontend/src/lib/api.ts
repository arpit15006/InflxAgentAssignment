const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Generate a unique session ID for multi-turn conversation tracking.
 */
export function generateSessionId(): string {
  return crypto.randomUUID();
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface ChatApiResponse {
  response: string;
}

/**
 * Send a message to the Inflx AI agent backend.
 *
 * @param message - User's message text
 * @param sessionId - Session ID for multi-turn tracking
 * @returns Agent's response string
 */
export async function sendMessage(
  message: string,
  sessionId: string
): Promise<string> {
  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: message.trim(),
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    const data: ChatApiResponse = await response.json();
    return data.response;
  } catch (error) {
    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw new Error(
        "Unable to connect to the server. Please ensure the backend is running on port 8000."
      );
    }
    throw error;
  }
}
