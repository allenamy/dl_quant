import sys; sys.argv=["x","none"]
exec(open("/workspace/uplift_2026-09-11/r2_sleeve/drive2_r2.py").read().replace("if __name__==\"__main__\":","if False:"))
stage3(); print("DONE_stage3",flush=True)
