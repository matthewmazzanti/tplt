{ pkgs ? import <nixpkgs> {}, ... }:
with pkgs;
let
  pyPkgs = p: with p; [
    GitPython
  ];

  python = python3.withPackages pyPkgs;
in pkgs.mkShell {
  buildInputs = with pkgs; [ python ];
}
