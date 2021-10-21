---
layout: default
---

# Education

- **2021/09-至今：**哈尔滨工业大学（深圳）控制科学与工程(推免生)
- **2017/09-2021/06：**哈尔滨工业大学（深圳）自动化专业

我的研究聚焦于**机器人的感知定位与运动规划**，现于[陈浩耀](faculty.hitsz.edu.cn/chenhaoyao)教授带领的[网络机器人与系统实验室（NRSL）]([NRSL十二周年纪念2009-2021 (nrs-lab.com)](http://nrs-lab.com/))攻读学术型研究生学位。

**主修课程：**高等代数、数学分析、自动控制原理、自动控制实践、数字图像处理、[机器视觉](https://github.com/jianhengLiu/20Machine-Vision-Course)、系统建模与仿真、数学规划、[机器人学导论](https://github.com/jianhengLiu/20Robotics-Course)、最优控制、[移动机器人运动规划](https://github.com/jianhengLiu/MotionPlanningForMobileRobot)

# Publication

- **Vision-encoder-based Payload State Estimation for Autonomous MAV With a Suspended Payload**<br/>
   **Jianheng Liu**\*, Yunfan Ren\*, Haoyao Chen and Yunhui Liu<br/>
   IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS, 2021)

*\* denotes equal contribution*



# Honors & Awards

- 2019-2020一等奖学金，2018-2019三等奖学金，2017-2018二等奖学金
- 2020ROBOCON国家一等奖，2019ROBOCON国家二等奖
- 2019挑战杯国家三等奖，2019互联网+黑龙江省铜奖，2019哈工大“祖光杯”深圳校区金奖
- 2018全国大学生英语竞赛C类二等奖
- 2018国际青少年无人机大赛大满贯特等奖

# Research

<table>
<td  width="45%" style="vertical-align:middle;">
<video controls autoplay muted>
                <source src="./index.assets/dynamic-vins.mp4">
            </video><br/>
[<a href="https://github.com/jianhengLiu/YOLOv3-Atlas-ROS">YOLOv3-Atlas-ROS</a>]
</td>
<td width="55%" style="vertical-align:top;">
    <strong>Dynamic-VINS</strong><br/>
        Dynamic-VINS is a SLAM system based on <a href="https://github.com/jianhengLiu/VINS-RGBD-FAST">VINS-RGBD-FAST</a>. I try to combine YOLOv3 to eliminate the impact of the dynamic feature to SLAM system. The whole system is conducted in HUAWEI Atlas 200DK. A resposity adapting YOLOv3 and ROS to Atlas200DK is release to <a href="https://github.com/jianhengLiu/YOLOv3-Atlas-ROS">YOLOv3-Atlas-ROS</a>. And more feature is on the development.
    </td>
</table> 



<table>
<td  width="45%" style="vertical-align:middle;"><img src="./index.assets/positioning.gif"/><br/>
    [<a href="https://github.com/jianhengLiu/VINS-RGBD-FAST">Code</a>]</td>
<td width="55%" style="vertical-align:top;">
    <strong>VINS-RGBD-FAST</strong><br/>
        VINS-RGBD-FAST is a SLAM system based on VINS-RGBD. I do some refinements to accelerate the system's performance in resource-constrained embedded paltform, like HUAWEI Atlas 200DK, Raspberry Pi. 
    <li>extract FAST feature instead of Harris feature and solved feature clusttering problem</li>
    <li>added stationary initialization</li>
    <li>added IMU-aided feature tracking and extracted-feature area's quality judgement</li>
    <li>lower the required bandwidth of the system</li>
    <li>trade-off of accuracy and efficiency by constrain the optimized variables in backend</li>
    </td>
</table> 



<table>
<td  width="45%" style="vertical-align:middle;">
<iframe src="https://player.bilibili.com/player.html?aid=590278777&cid=4046807133&page=1&as_wide=0&high_quality=1" scrolling="no" border="0" frameborder="0" framespacing="0" allowfullscreen="true"> </iframe><br/>
    [<a href="https://github.com/jianhengLiu/Vision-encoder-based-Payload-State-Estimator">Code</a>] 
    [<a href="https://www.bilibili.com/video/BV1Qq4y1U7n4?share_source=copy_web">Video</a>] 
    </td>
<td width="55%" style="vertical-align:top;">
    <strong>Vision-encoder-based Payload State Estimation for Autonomous MAV With a Suspended Payload</strong><br/>
<strong>Jianheng Liu*</strong>, Yunfan Ren*, Haoyao Chen and Yunhui Liu<br/>
<i>IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS, 2021)</i><br/>
        We develops a novel real-time system for estimating the payload position; the system consists of a monocular fisheye camera and a novel encoder-based device. A Gaussian fusion-based estimation algorithm is developed to obtain the payload state estimation. Based on the robust payload position estimation, a payload controller is presented to ensure the reliable tracking performance on aggressive trajectories. Several experiments are performed to validate the high performance of the proposed method.
    </td>
</table>



<table>
<td  width="45%" style="vertical-align:middle;">
<iframe src="https://player.bilibili.com/player.html?aid=632887496&bvid=BV1gb4y127by&cid=405321402&page=1&as_wide=0&high_quality=1" scrolling="no" border="0" frameborder="no" framespacing="0" allowfullscreen="true"> </iframe><br/>
    [<a href="https://www.bilibili.com/video/BV1gb4y127by?share_source=copy_web">Video</a>] 
</td>
<td width="55%" style="vertical-align:top;">
    <strong>MatRix</strong><br/>
    2020智能科创C端训练营作品MatRix！<br/>
    一个可交互的智能地毯，能够通过防呆设计的磁吸接口实现无限拼接，
    MatRix可以作为你家庭的智能终端，游戏机，装饰品等等。
    </td>
</table> 





<table>
<td  width="45%" style="vertical-align:middle;">
    <iframe src="https://player.bilibili.com/player.html?aid=250421025&bvid=BV1xv411w7Md&cid=405321832&page=0&as_wide=0&high_quality=1" scrolling="no" border="0" frameborder="no" framespacing="0" allowfullscreen="true"> </iframe><br/>
    [<a href="https://github.com/jianhengLiu/quad_controller_SE3">Code</a>]
    [<a href="https://www.bilibili.com/video/BV1xv411w7Md?share_source=copy_web">Video</a>]
    </td>
<td width="55%" style="vertical-align:top;">
    <strong>quad_controller_SE3</strong><br/>
quadrotor controller based on SE3 geometric control.
    </td>
</table> 





<table>
<td  width="45%" style="vertical-align:middle;"><img src="./index.assets/bezier.png"/><br/>
    [<a href="https://github.com/jianhengLiu/BezierTrajGenerator">BezierTrajGenerator</a>]
    [<a href="https://github.com/jianhengLiu/MinimumSnapTrajGenerator">MinimumSnapTrajGenerator</a>]
    [<a href="https://github.com/jianhengLiu/MapManager">MapManager</a>]
    </td>
<td width="55%" style="vertical-align:top;">
    <strong>BezierTrajGenerator/MinimumSnapTrajGenerator</strong><br/>
    基于贝塞尔曲线以及基于最小化snap的移动机器人轨迹规划算法，同时开发了二维地图管理工具<a href="https://github.com/jianhengLiu/MapManager">MapManager</a>用于算法验证及可视化
    </td>
</table> 



<table>
<td  width="45%" style="vertical-align:middle;">
    <iframe src="https://player.bilibili.com/player.html?aid=547978814&bvid=BV1rq4y1N76T&cid=405322254&page=1&as_wide=0&high_quality=1" scrolling="no" border="0" frameborder="no" framespacing="0" allowfullscreen="true"> </iframe><br/>
    [<a href="https://github.com/jianhengLiu/FlightController">Code</a>]
    [<a href="    https://www.bilibili.com/video/BV1rq4y1N76T?share_source=copy_web">Video</a>]
    </td>
<td width="55%" style="vertical-align:top;">
    <strong>FlightController</strong><br/>
基于ROS，C ++和coppeliaSim的四旋翼无人机控制仿真模型 采用动力学模型重构的控制器，计算升力f以及力矩M，并通过控制分配矩阵控制各电机转速，实现无人机控制
    </td>
</table> 





<table>
<td  width="45%" style="vertical-align:middle;"><img src="./index.assets/steeringwheel.png"/><br/>
    [<a href="https://github.com/jianhengLiu/CoppeliaSim_Steeringwheel_Tutorial">Code</a>]</td>
<td width="55%" style="vertical-align:top;">
    <strong>CoppeliaSim/V-Rep舵轮教程</strong><br/>
一个基于CoppeliaSim/V-Rep仿真平台的舵轮底盘搭建教程，并利用ROS作为通讯架构控制底盘
    </td>
</table> 



<table>
<td  width="45%" style="vertical-align:middle;"><img src="./index.assets/manipulator.gif"/><br/>
    [<a href="https://github.com/jianhengLiu/Manipulator_GUI">Code</a>]</td>
<td width="55%" style="vertical-align:top;">
    <strong>Manipulator_GUI</strong><br/>
C++ Course Project (Complied in CodeBlocks)<br/>
    一个三关节平面机械臂的正逆运动学解算以及动画演示
    </td>
</table> 

