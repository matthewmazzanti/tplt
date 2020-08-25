{ pkgs ? import <nixpkgs> {} }:
with pkgs;
python3Packages.buildPythonApplication rec {
  pname = "tplt";
  version = "0.0.1";
  src = ./.;
  propagatedBuildInputs = with pkgs; [ python3Packages.GitPython ];
  meta = {
    description = "A simple git-based template manager";
  };
}
