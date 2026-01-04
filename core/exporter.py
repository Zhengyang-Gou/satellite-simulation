import os
import numpy as np
from datetime import datetime, timedelta

class DataExporter:
    def __init__(self):
        self.is_active = False
        self.export_dir = None
        self.start_time_ref = None
        self.end_time_ref = None
        self.step_counter = 0  # 用于生成有序的文件名 (step_0, step_1...)

    def start(self, parent_dir, current_time, duration_sec):
        """
        初始化导出：在 parent_dir 下创建一个新的子文件夹
        :param parent_dir: 用户选择的父目录
        :param current_time: 仿真当前时间
        :param duration_sec: 导出总时长 (秒)
        """
        try:
            # 1. 创建带时间戳的子文件夹，防止文件散乱
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = f"Export_{timestamp}"
            self.export_dir = os.path.join(parent_dir, folder_name)
            
            if not os.path.exists(self.export_dir):
                os.makedirs(self.export_dir)

            # 2. 设置状态
            self.is_active = True
            self.step_counter = 0
            self.start_time_ref = current_time
            # 使用秒计算结束时间
            self.end_time_ref = current_time + timedelta(seconds=duration_sec)
            
            return True, f"Saving to {folder_name}"
            
        except Exception as e:
            self.stop()
            return False, str(e)

    def record_frame(self, current_time, satellites, isl_indices, gsl_indices):
        """
        记录当前这一帧：创建一个新的 .txt 文件并写入所有数据
        """
        if not self.is_active or not self.export_dir: return

        try:
            # 1. 构造文件名 (使用 step 计数器保证排序，使用时间戳保证可读性)
            # 例如: step_0001_2023-10-25_12-00-10.txt
            t_str_safe = current_time.strftime("%Y-%m-%d_%H-%M-%S")
            fname = f"step_{self.step_counter:04d}_{t_str_safe}.txt"
            fpath = os.path.join(self.export_dir, fname)
            
            t_str_display = current_time.strftime("%Y-%m-%d %H:%M:%S")

            with open(fpath, 'w') as f:
                # --- A. 写入元数据 ---
                f.write("[METADATA]\n")
                f.write(f"Time: {t_str_display}\n")
                f.write(f"Step: {self.step_counter}\n")
                f.write(f"Total_Sats: {len(satellites)}\n")
                f.write("\n")

                # --- B. 写入节点 (Nodes) ---
                f.write("[NODES]\n")
                f.write("ID, Name, X_ECEF, Y_ECEF, Z_ECEF\n") # 表头
                
                # 建立临时索引映射 (Index -> SatID)，方便 Link 写入
                idx_to_id = {}
                
                for i, s in enumerate(satellites):
                    # 记录映射关系
                    idx_to_id[i] = s.sat_id
                    
                    # 过滤无效坐标 (未被过滤器选中的卫星通常坐标为0或极小)
                    if np.linalg.norm(s.position) > 100:
                        f.write(f"{s.sat_id}, {s.name}, {s.position[0]:.2f}, {s.position[1]:.2f}, {s.position[2]:.2f}\n")
                
                f.write("\n")

                # --- C. 写入链路 (Links) ---
                f.write("[LINKS]\n")
                f.write("Type, SourceID, TargetID\n") # 表头

                # 写入 ISL
                # indices 格式: [2, idx_a, idx_b, 2, idx_c, idx_d ...]
                num_isl = len(isl_indices)
                if num_isl > 0:
                    for k in range(0, num_isl, 3):
                        idx_a = isl_indices[k+1]
                        idx_b = isl_indices[k+2]
                        
                        # 只有当两个端点都在 idx_to_id (即有效) 时才写入
                        if idx_a in idx_to_id and idx_b in idx_to_id:
                            f.write(f"ISL, {idx_to_id[idx_a]}, {idx_to_id[idx_b]}\n")

                # 写入 GSL
                num_gsl = len(gsl_indices)
                if num_gsl > 0:
                    for k in range(0, num_gsl, 3):
                        sat_idx = gsl_indices[k+1]
                        gs_idx = gsl_indices[k+2]
                        
                        if sat_idx in idx_to_id:
                            f.write(f"GSL, {idx_to_id[sat_idx]}, GS-{gs_idx}\n")

            # 计数器 +1
            self.step_counter += 1
                    
        except Exception as e:
            print(f"Export write error at step {self.step_counter}: {e}")

    def stop(self):
        """ 重置状态 """
        self.is_active = False
        self.export_dir = None
        self.start_time_ref = None
        self.end_time_ref = None
        self.step_counter = 0