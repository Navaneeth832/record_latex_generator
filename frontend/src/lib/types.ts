export type ProgramData = {
  title: string;
  code: string;
  output: string;
};

export type AlgorithmData = {
  name: string;
  steps: string[];
};

export type ExperimentData = {
  experiment_number: string;
  date: string;
  experiment_heading: string;
  aim: string;
  algorithms: AlgorithmData[];
  programs: ProgramData[];
  result: string;
};

export type TemplateForm = {
  name: string;
  lab_name: string;
  course_code: string;
  course_name: string;
  department: string;
  institution: string;
  semester: string;
  academic_year: string;
  submitted_to: string;
  submitted_by: string;
  roll_number: string;
  section: string;
  experiment_title: string;
  date: string;
};

export type TemplateSummary = {
  id: string;
  name: string;
  description: string;
  source: "builtin" | "uploaded";
  is_customizable: boolean;
  preview_url: string | null;
  download_filename: string;
};
