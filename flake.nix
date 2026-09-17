{
  description = "KanjiColorizer Anki addon";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    kanjivg = {
      url = "github:KanjiVG/kanjivg";
      flake = false;
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      kanjivg,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python311;

        version = self.rev or self.lastModifiedDate;

        pytestEnv = python.withPackages (ps: [
          ps.mock
          ps.pytest
        ]);

        kanjicolorizer = python.pkgs.buildPythonPackage {
          pname = "kanjicolorizer";
          inherit version;
          src = pkgs.lib.cleanSource ./.;
          format = "other";
          nativeBuildInputs = [ python.pkgs.setuptools ];
          buildPhase = ''
            python setup.py build
          '';
          installPhase = ''
            python setup.py install --prefix $out
          '';
          postPhases = "copyAssets";
          copyAssets = ''
            ASSETS_DIR=$out/${python.sitePackages}/kanjicolorizer/data/kanjivg/kanji
            mkdir -p "$ASSETS_DIR"
            cp -r ${kanjivg}/kanji/* "$ASSETS_DIR"/
          '';
          meta.mainProgram = "kanji_colorize";
        };

        kanji-colorize-src = pkgs.runCommand "kanji-colorize-src" { } ''
          mkdir -p $out

          cp ${./anki}/__init__.py $out/
          cp ${./anki}/kanji_colorizer.py $out/
          cp ${./anki}/config.json $out/
          cp ${./anki}/config.md $out/
          cp ${./anki}/manifest.json $out/

          mkdir -p $out/kanjicolorizer
          cp ${kanjicolorizer}/${python.sitePackages}/kanjicolorizer/__init__.py $out/kanjicolorizer/
          cp ${kanjicolorizer}/${python.sitePackages}/kanjicolorizer/colorizer.py $out/kanjicolorizer/

          cp ${python}/lib/${python.libPrefix}/argparse.py $out/kanjicolorizer/
          cp ${python}/lib/${python.libPrefix}/colorsys.py $out/kanjicolorizer/

          mkdir -p $out/kanjicolorizer/licenses
          cp -r ${./licenses}/* $out/kanjicolorizer/licenses/
        '';

        kanji-colorize = pkgs.runCommand "kanji-colorize" { } ''
          mkdir -p $out

          cp --no-preserve=mode -r ${kanji-colorize-src}/* $out/

          mkdir -p $out/kanjicolorizer/data/kanjivg
          cp -r ${kanjivg}/kanji $out/kanjicolorizer/data/kanjivg/
        '';

        tests-src = pkgs.runCommand "kanji-colorize-tests-src" { } ''
          mkdir -p $out/kanjicolorizer/data

          cp --no-preserve=mode -r ${./kanjicolorizer}/*.py $out/kanjicolorizer/
          cp -r ${./kanjicolorizer}/tests $out/kanjicolorizer/
          ln -s ${kanjivg} $out/kanjicolorizer/data/kanjivg
          cp -r ${./test}/. $out/test
          cp ${./pytest.ini} $out/pytest.ini
        '';
      in
      {
        packages = {
          default = kanjicolorizer;
          kanjicolorizer = kanjicolorizer;
          kanji-colorize = kanji-colorize;
          kanji-colorize-anki-addon = pkgs.anki-utils.buildAnkiAddon {
            pname = "kanji-colorize";
            inherit version;
            src = kanji-colorize-src;
            postPhases = "copyAssets";
            copyAssets = ''
              ASSETS_DIR=$out/share/anki/addons/kanji-colorize/kanjicolorizer/data/kanjivg
              mkdir -p "$ASSETS_DIR"
              cp -r ${kanjivg}/kanji "$ASSETS_DIR"/
            '';
          };
        };

        checks = {
          default =
            pkgs.runCommand "kanji-colorize-tests"
              {
                nativeBuildInputs = [
                  python
                  pytestEnv
                ];
                testsSrc = tests-src;
              }
              ''
                mkdir -p testroot
                cp --no-preserve=mode -r $testsSrc/. testroot
                cd testroot
                pytest
                touch $out
              '';
        };

        devShells.default = pkgs.mkShell {
          packages = [ pytestEnv ];
          shellHook = ''
            KANJIVG_DIR="./kanjicolorizer/data/kanjivg"

            if [ ! -e "$KANJIVG_DIR" ] || [ -L "$KANJIVG_DIR" ]; then
              ln -sfn ${kanjivg} "$KANJIVG_DIR"
            else
              echo "Warning: $KANJIVG_DIR is a standard directory"
              echo "Please run 'rm -rf $KANJIVG_DIR' so the devShell can symlink it"
            fi
          '';
        };
      }
    );
}
