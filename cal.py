import random
from   tqdm import tqdm
import save
from road import RoadManager 
import car
import time as t
import datetime

def simulation( time_max,
                generate_time_max,
                SEED,
                highway_queue,
                detour_queue,
                ratio_type,
                jam_prevision_vel,
                JAD_active,
                target_vol,
                avoiding_sec
                ):
    '''
    シミュレーションの本体
    '''

    #シード値固定
    #この行以前にrandomモジュールを使用しないこと
    random.seed(SEED)

    #シミュレーションの処理時間を計測するための現在時刻記録
    start_time = t.time()

    #print("\nSEED",seed)
    #####ここから初期化部#####
    time_max = time_max*10#0.1秒間隔で計算する。例えば600秒分計算するなら6000回計算することになる。
    generate_time_max = generate_time_max*10#0.1秒間隔で計算するので揃える

    ###道路生成###

    #道路のパラメータを設定
    #高速道路
    highway = dict( queue = highway_queue,
                    generate_time_max = generate_time_max,
                    vel_hope_max = (0,90,100),
                    road_length = 5000,
                    sag = {"start":4000, "end":5000, "gravity_accl":-0.294},
                    ratio_type = ratio_type,
                    jam_prevision_vel = jam_prevision_vel,
                    ic_pos = (1900,5000),
                    seed = SEED,
                    )

    #一般道路
    generalway = dict(  queue = detour_queue,
                        generate_time_max = generate_time_max,
                        #第一車線は迂回した車を一旦受け入れる車線用
                        vel_hope_max = (55,70,70),
                        road_length = 5000,
                        #一般道にサグはないと仮定するので影響しない値を設定
                        sag = {"start":-2, "end":-1, "gravity_accl":-0.294},
                        #一般道路にはType0,1のみ発生させることを想定
                        ratio_type = ratio_type,
                        jam_prevision_vel = jam_prevision_vel,
                        ic_pos = (),
                        seed = SEED
                        )

    #道路インスタンスを作成
    roadmanager = RoadManager(time_max)
    roadmanager.append(highway)
    roadmanager.append(generalway)
    road_list = roadmanager.get_list()

    car_max = 0
    for road in road_list:
        car_max += road.car_max

    ###/道路生成###

    ###ログ出力の設定###

    #旅行時間記録用リスト作成
    traveltime_list = dict( highway = [],
                            general = [],
                            detour  = [])

    #ログの出力間隔・ログの可視化間隔を指定
    interval = 10

    #ログ用リスト作成
    log = []

    ###/ログ出力の設定###

    #乱数テーブルリセット
    random.seed(SEED)
    
    #####ここまで初期化部#####

    #######シミュレーション開始#######
    for time in range(time_max):#tqdm(range(time_max),desc="\tSimulation"):#シミュレーションする時間だけループ

        for road in road_list:#道路の数だけループ
            
            #加速度を除く車両の情報を更新
            road.update_car_info(time)

            #渋滞回避のための道路離脱【渡邊修論】
            #road.jam_mitigation_control(time,JAD_active,target_vol,detour_road = road_list[1],avoiding_time = avoiding_time)
            road.detour_control_yamauchi(time = time,target_vol = target_vol,detour_road=road_list[1],avoiding_sec = avoiding_sec)

            #車線ごとに前方位置順にIDを並べたリストを更新
            road.update_lane_lists()

            #最後の車両IDを更新
            road.update_last_car()

            #加速度を更新 車線変更時は、車線変更を考慮した加速度を算出する。
            road.update_accl()

            #車線変更処理
            road.change_lane(time)

            #車両発生
            road.generate_car(time)

            #車両削除 
            road.remove_car(time,traveltime_list)

            #ログ記録 intervalの値だけ時間が経過したら車両情報をログに出力
            if time%interval == 0:
                for run_car in road.run_car_list:
                    log.append(run_car.log_out_obj(time))

    #シミュレーションの処理時間を計測
    end_time = t.time()
    prc_time = str(datetime.timedelta(seconds = end_time - start_time))

    #######シミュレーション終了#######

    ########記録開始########
    #xlsx出力ファイル作成
    save.save(  log,
                traveltime_list,
                car_max,
                time_max,
                generate_time_max,
                interval,
                road_list,
                SEED,
                prc_time,
                ratio_type,
                jam_prevision_vel,
                JAD_active,
                target_vol,
                avoiding_sec
                )
    ########記録終了########

    end_time = t.time()
    prc_time = str(datetime.timedelta(seconds = end_time - start_time))
    print("\tTime",prc_time)
