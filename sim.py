import cal
import sys
import itertools
from joblib import Parallel, delayed
from sympy import sieve

TIME_MAX = 1200             #シミュレーションを行う時間の長さ[秒]
GENERATE_TIME_MAX = 720    #車両生成を行う時間の長さ[秒]

def listparam_run_simulation(   SEED,
                                highway_queue,
                                detour_queue,
                                ratio_type,
                                jam_prevision_vel,
                                JAD_active,
                                target_vol,
                                avoiding_sec):
    '''
    各パラメータを設定し、シミュレーションを実行
    '''

    cal.simulation( TIME_MAX,
                    GENERATE_TIME_MAX,
                    SEED,
                    highway_queue,
                    detour_queue,
                    ratio_type,
                    jam_prevision_vel,
                    JAD_active,
                    target_vol,
                    avoiding_sec
                    ) 

if __name__ == "__main__":

    print("===START===")

    ###シミュレーションに渡すパラメータ設定###

    #シード値指定()

    #シード探索用 1~100までの素数リスト
    #SEED_LIST = [i for i in sieve.primerange(1,100)]

    #渋滞シード
    SEED_LIST = [2,3,5,7,13,17,23,37,53,67]

    #無渋滞シード
    #SEED_LIST = [11,29,31,41,43,47,59,61,71,79]

    #高速道路交通量(highwayインスタンス作成時に使用)
    highway_queue_list = [(0,480,480)]
    
    #迂回先交通量(generalインスタンス作成時に使用)
    detour_queue_list  = [(0,400,400)]

    #車両Type比率 左からType0車両，Type1車両，Type2車両
    #Type:0 = 自動運転車両。サグ部で減速せず、鈍化もしない。
    #Type:1 = 一般運転車両。サグ部で減速しないが、鈍化はする。
    #Type:2 = 一般運転車両。サグ部で減速し、鈍化もする。
    ratio_type_list = [(0.6,0.0,0.4)]

    #渋滞予見閾値(km/h)
    jam_prevision_vel_list = [60]

    #渋滞吸収運転をするか否か(0じゃないなら行う)
    JAD_active_list = [0]

    #目標交通量(0の場合は迂回制御を行わない)
    target_vol_list = [1700]
    #target_vol_list = [0]

    #迂回制御時間[s]
    avoiding_sec_list = [120]

    #並列処理させる際に回すパラメータ総当たりリスト作成
    parallel_prm_list = itertools.product(  SEED_LIST,
                                            highway_queue_list,
                                            detour_queue_list,
                                            ratio_type_list,
                                            jam_prevision_vel_list,
                                            JAD_active_list,
                                            target_vol_list,
                                            avoiding_sec_list)

    #n_jobsに並列プロセス数を入力(CPUとメモリによって調節)
    #デバッグ実行時はn_jobs=1
    #n_jobs=-1で最大プロセス数(CPU最大コア数)
    Parallel(n_jobs=1)([delayed(listparam_run_simulation)(*prm) for prm in parallel_prm_list])

    print("===FINISH===")