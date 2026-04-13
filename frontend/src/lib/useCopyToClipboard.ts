"use client";

type CopyResult = {
  ok: boolean;
  error?: string;
};

function fallbackCopy(text: string) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "fixed";
  textarea.style.top = "0";
  textarea.style.left = "-9999px";
  textarea.style.opacity = "0";

  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  textarea.setSelectionRange(0, textarea.value.length);

  try {
    return document.execCommand("copy");
  } finally {
    document.body.removeChild(textarea);
  }
}

export function useCopyToClipboard() {
  const copy = async (text: string): Promise<CopyResult> => {
    if (typeof document === "undefined") {
      return { ok: false, error: "Clipboard is only available in the browser." };
    }

    if (!text) {
      return { ok: false, error: "There is nothing to copy yet." };
    }

    if (!document.hasFocus()) {
      const copied = fallbackCopy(text);
      if (copied) {
        return { ok: true };
      }

      return {
        ok: false,
        error: "The tab is not focused. Focus the page and try again.",
      };
    }

    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        return { ok: true };
      } catch {
        const copied = fallbackCopy(text);
        if (copied) {
          return { ok: true };
        }

        return {
          ok: false,
          error: "Clipboard access was blocked by the browser.",
        };
      }
    }

    const copied = fallbackCopy(text);
    if (copied) {
      return { ok: true };
    }

    return {
      ok: false,
      error: "Copy is not supported in this browser or environment.",
    };
  };

  return { copy };
}
