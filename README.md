# Quadruped Simulation: CHAMP, ROS 2 Humble and Gazebo

Simulation workspace for walking a quadruped robot with the [CHAMP](https://github.com/chvmp/champ) gait controller in Gazebo Classic.

`robot2` is our robot package. It currently uses a Yobotics / mini-cheetah-style URDF as a stand-in until the team's own robot model is ready. Everything here (config files, launch files, the control chain) is set up so the stand-in can be swapped for the real URDF without restructuring anything.

## Repository layout

```
.
├── src/
│   ├── robot2/                  # our robot package
│   │   ├── config/              # gait, joints, links, ros_control YAML files
│   │   ├── launch/              # gazebo.launch.py (full simulation)
│   │   ├── urdf/  xacro/        # robot description
│   │   └── worlds/              # Gazebo world
│   ├── yobotics_description/    # visual meshes for the stand-in robot
│   └── unitree-go2-ros2/        # CHAMP for ROS 2 (git submodule, our fork)
├── .gitignore
└── README.md
```

CHAMP is not copied into this repo. It is a pinned git submodule pointing at our fork, which contains a few small launch-file fixes (the URDF text is wrapped in `ParameterValue(..., value_type=str)` so launch does not try to parse it as YAML).

## Requirements

- Ubuntu 22.04 (native or WSL2)
- ROS 2 Humble
- Gazebo Classic 11 (installed with `ros-humble-gazebo-ros-pkgs`)

## Setup

### 1. Clone with submodules

```bash
git clone --recurse-submodules https://github.com/MasonNjos/BARC
cd barc
```

If you already cloned without `--recurse-submodules`, run:

```bash
git submodule update --init --recursive
```

### 2. Install dependencies

```bash
sudo apt install -y \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-gazebo-ros2-control \
  ros-humble-xacro \
  ros-humble-robot-localization \
  ros-humble-ros2-control \
  ros-humble-ros2-controllers \
  ros-humble-teleop-twist-keyboard \
  ros-humble-velodyne \
  ros-humble-velodyne-gazebo-plugins \
  ros-humble-velodyne-description \
  python3-rosdep python3-colcon-common-extensions

# first time only
sudo rosdep init
rosdep update

rosdep install --from-paths src --ignore-src -r -y
```

### 3. Build

```bash
source /opt/ros/humble/setup.bash
colcon build
source install/setup.bash
```

`ros2 launch` runs from `install/`, not `src/`. After editing anything in `robot2`, rebuild and source again:

```bash
colcon build --packages-select robot2
source install/setup.bash
```

## Running the simulation

```bash
LIBGL_ALWAYS_SOFTWARE=1 ros2 launch robot2 gazebo.launch.py
```

`LIBGL_ALWAYS_SOFTWARE=1` forces software rendering, which is needed on WSL2 without GPU passthrough. Drop it if your GPU rendering works.

To drive the robot, open a second terminal, source the workspace, and run:

```bash
source install/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

`champ_teleop` is an alternative (`ros2 run champ_teleop champ_teleop.py`). You can also publish directly:

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}}"
```

Keep commands under the limits in `gait.yaml` (0.2 m/s forward, 0.1 m/s sideways, 0.45 rad/s turning).

If Gazebo is left running after you close the launch, stop it with `killall gzserver gzclient` before relaunching.

## How a keypress becomes motion

```
teleop  ->  /cmd_vel  ->  quadruped_controller_node  ->  joint trajectory
        ->  joint_group_effort_controller (PID)  ->  gazebo_ros2_control  ->  Gazebo physics
                                  ^                                               |
                                  +------------------ /joint_states -------------+
```

| Stage | What it does |
|---|---|
| Teleop | Publishes a `geometry_msgs/Twist` on `/cmd_vel` |
| `quadruped_controller_node` (CHAMP) | Plans the gait and runs inverse kinematics to get joint angles |
| `joint_group_effort_controller` | PID controller that turns target angles into joint torques |
| `gazebo_ros2_control` | Gazebo plugin that hosts `controller_manager` and applies torques to the simulated joints |
| Gazebo | Simulates the physics. Joint states are fed back to the controllers |

On a physical robot, only the bottom of this chain changes: `gazebo_ros2_control` is replaced by a hardware interface that talks to the motor drivers, and the keyboard is replaced by the remote control.

## Configuration files (`src/robot2/config/`)

| File | Purpose | Must match |
|---|---|---|
| `joints/joints.yaml` | Maps each leg to its three actuated joints (hip, thigh, calf) | Joint names in the URDF |
| `links/links.yaml` | Maps each leg to its links, and sets the base link | Link names in the URDF. `base` must be the URDF's real root link (`trunk`) |
| `gait/gait.yaml` | Gait tuning: step height, speed limits, knee orientation, standing height | Robot geometry. Current values are untuned starting points |
| `ros_control/ros_control.yaml` | `controller_manager` setup, controllers, effort command interface, PID gains | The `<ros2_control>` joints and interfaces in the URDF |

ROS 2 parameter files are strict about structure. `joints.yaml`, `links.yaml` and `gait.yaml` must be wrapped like this, with consistent indentation, or nodes crash on startup:

```yaml
/**:
  ros__parameters:
    joints_map:
      left_front:
        - FL_hip_joint
        ...
```

`ros__parameters` has two underscores.

## Meshes

The URDF refers to meshes as `package://yobotics_description/meshes/*.STL`. Gazebo Classic does not resolve `package://` through ROS, so `launch/gazebo.launch.py` adds the mesh package's install `share` directory to `GAZEBO_MODEL_PATH` before Gazebo starts. Without this, the robot is only visible with View > Collisions turned on.

The STL files are decimated (about 2,000 to 6,000 triangles each). The originals, up to 213,000 triangles each, froze Gazebo under software rendering. Filenames are case-sensitive on Linux (`trunk.STL`, not `trunk.stl`).

## Using a different robot (for example the team's URDF)

1. Put the URDF or xacro in `src/robot2/xacro/` and update `default_model_path` in `launch/gazebo.launch.py`.
2. Add a `<ros2_control>` block to the URDF with every actuated joint (`effort` command interface, `position` and `velocity` state interfaces), plus the `gazebo_ros2_control` plugin block pointing at `ros_control.yaml` via `$(find robot2)`.
3. Update `joints.yaml`, `links.yaml` and the joint list and gains in `ros_control.yaml` to the new joint and link names.
4. If the model uses meshes, put them in a package, make sure the launch file adds that package's `share` directory to `GAZEBO_MODEL_PATH`, and decimate heavy CAD exports. Check units: a millimeter export needs `scale="0.001 0.001 0.001"`.
5. Check `spawn height` (`world_init_z` in the launch file) against the robot's standing height so the feet do not start inside the ground.
6. Rebuild, source, and retune `gait.yaml` and the gains.

Avoid `word: ` (a colon followed by a space) inside comments or text in the xacro. Launch tries to parse the processed URDF as YAML and fails on it.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Package or file not found after an edit | `install/` is stale. Rebuild and source. If it persists: `rm -rf build/robot2 install/robot2`, then rebuild |
| `/controller_manager` never appears | A `<ros2_control>` block is missing joints, the plugin path in the URDF is wrong, or `ros_control.yaml` has a structure or indentation error |
| `Couldn't parse params file ... Sequences can only be values and not keys` | A YAML file is missing the `/**: ros__parameters:` wrapper, or its indentation is wrong |
| `Unable to parse the value of parameter robot_description as yaml` | A colon-space in a comment or text in the xacro. Find it with `xacro <file> > /tmp/r.urdf` and parse `/tmp/r.urdf` with PyYAML to get the line |
| Robot only visible with Collisions on | Mesh package not built or sourced, wrong filename case, or its `share` directory is not on `GAZEBO_MODEL_PATH` |
| Gazebo window freezes on startup | Software rendering is overloaded. Keep shadows off in `worlds/default.world` and keep meshes decimated |
| Control nodes crash with "No links config file provided" | The YAML files are not installed into `install/`, or are not in the per-file subfolders (`config/links/links.yaml`) |
| Submodule folder is empty | Run `git submodule update --init --recursive` |

## Known issues

- Gait and gain values are untuned starting points. Expect legs to shake (lower `p`) or sag (raise `p`) until tuned.
- The stand-in URDF contains old ROS 1 plugin blocks. Log lines such as `gazebo_ros_force: Force plugin missing <link_name>` and `p3d_base_controller: Missing <body_name>` come from these and do not affect the simulation.
- `Parameter 'hold_joints' has already been declared` appears once per `<ros2_control>` block. The controllers still load.
- The lidar and camera visuals use meshes from `hector_sensors_description`, which is not installed, so they do not render.

## Planned work

- Simulate a depth camera and a 4D LiDAR in the CHAMP Gazebo setup.
- Swap the stand-in URDF for the team's robot once the CAD is ready.

## Repository notes

- Do not commit `build/`, `install/` or `log/`. They are in `.gitignore`, along with Windows `:Zone.Identifier` files.
- CHAMP is pinned. To update it, check out the new commit inside `src/unitree-go2-ros2` and commit the updated submodule pointer here.

## Credits and licenses

- [CHAMP](https://github.com/chvmp/champ) controller, and the ROS 2 port used here from the `unitree-go2-ros2` repository.
- Stand-in robot model and meshes adapted from [HitSZwang/mini-cheetah-gazebo-urdf](https://github.com/HitSZwang/mini-cheetah-gazebo-urdf). The STL files in this repo are decimated copies.

Third-party components keep their own licenses. Add a license for our own code here.
