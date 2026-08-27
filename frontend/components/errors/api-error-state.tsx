import Link from "next/link";
import { ApiClientError } from "@/lib/api-client";

interface ApiErrorPresentation {
  title: string;
  message: string;
  signIn: boolean;
}

export function getApiErrorPresentation(
  error: unknown,
  fallbackTitle: string,
  fallbackMessage: string,
): ApiErrorPresentation {
  const status = error instanceof ApiClientError ? error.status : undefined;
  switch (status) {
    case 401:
      return { title: "Your session has expired", message: "Sign in again to continue.", signIn: true };
    case 403:
      return { title: "Access denied", message: "You do not have permission to access this resource.", signIn: false };
    case 404:
      return { title: "Resource not found", message: "The requested resource is unavailable or has been removed.", signIn: false };
    case 429:
      return { title: "Request limit reached", message: "Please wait a moment before trying again.", signIn: false };
    case 500:
      return { title: "Service unavailable", message: "The server could not complete the request. Please try again.", signIn: false };
    case undefined:
      return { title: "Backend unavailable", message: "Check your network connection and try again.", signIn: false };
    default:
      return { title: fallbackTitle, message: fallbackMessage, signIn: false };
  }
}

export function ApiErrorState({
  error,
  fallbackTitle,
  fallbackMessage,
}: {
  error: unknown;
  fallbackTitle: string;
  fallbackMessage: string;
}) {
  const presentation = getApiErrorPresentation(error, fallbackTitle, fallbackMessage);
  return <div className="retrieval-state retrieval-error" role="alert">
    <h2>{presentation.title}</h2>
    <p>{presentation.message}</p>
    {presentation.signIn && <Link className="secondary-button" href="/login">Return to sign in</Link>}
  </div>;
}
