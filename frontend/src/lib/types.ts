export type ProgramData = {
  title: string;
  code: string;
  dependencies: string[];
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
  title: string;
  aim: string;
  algorithms: AlgorithmData[];
  programs: ProgramData[];
  result: string;
};
