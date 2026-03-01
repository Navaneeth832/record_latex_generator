export type ParsedProgram = {
  title: string;
  code: string;
};

export function parseProgramsFromText(rawText: string): ParsedProgram[] {
  const lines = rawText.split(/\r?\n/);
  const programs: ParsedProgram[] = [];

  let currentTitle = "";
  let currentCode: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();

    if (trimmed.startsWith("###")) {
      const code = currentCode.join("\n").trim();
      if (code) {
        programs.push({
          title: currentTitle || `Program ${programs.length + 1}`,
          code,
        });
      }

      currentTitle = trimmed.slice(3).trim() || `Program ${programs.length + 1}`;
      currentCode = [];
      continue;
    }

    currentCode.push(line);
  }

  const finalCode = currentCode.join("\n").trim();
  if (finalCode) {
    programs.push({
      title: currentTitle || `Program ${programs.length + 1}`,
      code: finalCode,
    });
  }

  return programs;
}
