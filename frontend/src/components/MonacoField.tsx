"use client";

import dynamic from "next/dynamic";

const Editor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

type Props = {
  label: string;
  language: string;
  value: string;
  onChange: (value: string) => void;
  minHeight?: string;
};

export default function MonacoField({
  label,
  language,
  value,
  onChange,
  minHeight = "200px",
}: Props) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-semibold">{label}</label>
      <Editor
        height={minHeight}
        language={language}
        value={value}
        onChange={(v) => onChange(v ?? "")}
        theme="vs-dark"
        options={{ minimap: { enabled: false }, wordWrap: "on" }}
      />
    </div>
  );
}
