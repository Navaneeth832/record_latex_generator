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
