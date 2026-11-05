#!/usr/bin/env python3

import re
import subprocess
import sys

def main():
    xacro_path = sys.argv[1]

    result = subprocess.run(
        ["xacro", xacro_path],
        capture_output=True,
        text=True,
        check=True
    )

    # Remove XML comments from the generated URDF.
    urdf = re.sub(r"<!--.*?-->", "", result.stdout, flags=re.DOTALL)

    # Output only the cleaned URDF.
    sys.stdout.write(urdf)

if __name__ == "__main__":
    main()
