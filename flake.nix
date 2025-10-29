{
  description = "ValueCell - A community-driven, multi-agent platform for financial applications";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Python environment with uv
        pythonEnv = pkgs.python312.withPackages (
          ps: with ps; [
            # Add any system-level Python packages if needed
          ]
        );

        # Development shell with all required tools
        devShell = pkgs.mkShell {
          buildInputs = with pkgs; [

            uv # Python package manager

            # Node.js ecosystem
            bun # JavaScript runtime and package manager

          ];

          shellHook = ''
            echo "Welcome to ValueCell development environment!"
            echo "Python: $(python --version)"
            echo "UV: $(uv --version)"
            echo "Bun: $(bun --version)"
            echo ""
            echo "Available commands:"
            echo "  - Python backend: cd python && uv run python -m valuecell"
            echo "  - Frontend: cd frontend && bun dev"
            echo "  - Install Python deps: cd python && uv sync"
            echo "  - Install frontend deps: cd frontend && bun install"
            echo ""
          '';

          # Environment variables
          PYTHONPATH = "${pythonEnv}/${pythonEnv.sitePackages}";
        };
      in
      {
        # Development shell
        devShells.default = devShell;

        # Packages (if needed)
        packages = {
          inherit devShell;
        };

        # App definitions (optional)
        apps = {
          dev = {
            type = "app";
            program = "${pkgs.writeShellScript "dev" ''
              echo "Starting ValueCell development environment..."
              echo "Starting Python backend in background..."
              cd python && uv run python -m valuecell &
              BACKEND_PID=$!

              echo "Starting frontend..."
              cd frontend && bun dev

              # Cleanup on exit
              kill $BACKEND_PID 2>/dev/null || true
            ''}";
          };
        };
      }
    );
}
