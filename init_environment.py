
import os
import shutil
import time

def clear_buffers():
    dirs = ["./seed_output", "./synthesis_final"]
    archive_dir = "./archive"
    
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)
        print(f"[INIT] Created archive directory: {archive_dir}")

    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"[INIT] Created directory: {d}")
        else:
            # Move files to archive
            files = os.listdir(d)
            if files:
                timestamp = int(time.time())
                arch_sub = os.path.join(archive_dir, f"{os.path.basename(d)}_{timestamp}")
                os.makedirs(arch_sub, exist_ok=True)
                
                for f in files:
                    src = os.path.join(d, f)
                    if os.path.isfile(src):
                        dst = os.path.join(arch_sub, f)
                        shutil.move(src, dst)
                print(f"[INIT] Archived {len(files)} files from {d} to {arch_sub}")
            else:
                print(f"[INIT] Directory {d} is clean.")

if __name__ == "__main__":
    clear_buffers()
