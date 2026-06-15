{ pkgs ? import <nixpkgs> {} }:

let
  # Define a python environment with your specific libraries
  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    #cryptography
    #pydantic
    discordpy
    python-dotenv
    openai
    pytest
  ]);
in
pkgs.mkShell {
  packages = [
    pythonEnv
    #sqlite
  ];

  shellHook = ''
    echo "Discord Ai Bot Development Environment Loaded"
    python --version
  '';
}