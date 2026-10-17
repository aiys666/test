--TABLE 3:ind.xly_reloan_num2
drop table if exists ind.xly_reloan_num2;

create table
    ind.xly_reloan_num2 as
SELECT
    CAST(t1.ID as varchar) biz_id,
    grant_strategy,
    baseinfo_onloan_hit_mid,
    baseinfo_m_onloan_hit_mid,
    if_hit_white_list,
    case
        when if_hit_white_list = 1 then 'WHITELIST'
        when grant_strategy = 'OLD'
        and baseinfo_m_onloan_hit_mid >= 1 THEN 'OLD_PLUS_M'
        when grant_strategy = 'OLD'
        and baseinfo_onloan_hit_mid >= 1 THEN 'OLD_PLUS'
        when grant_strategy = 'NEW'
        and mid_rn = 0 then 'NEW_PURE'
        when grant_strategy = 'NEW'
        and mid_rn > 0 then 'NEW_IMPURE'
        when grant_strategy = 'OLD' THEN 'OLD_SINGLE'
    end as is_reloan2
FROM
    (
        select
            a.id,
            grant_strategy,
            CASE
                WHEN C.baseinfo_onloan_hit_mid IS NULL THEN B.baseinfo_onloan_hit_mid
                ELSE C.baseinfo_onloan_hit_mid
            END AS baseinfo_onloan_hit_mid,
            baseinfo_m_onloan_hit_mid
        from
            ind.xly_reloan_num a
            left join (
                select
                    mid,
                    date (date_parse (data_date, '%Y%m%d')) as data_date,
                    max(onloan_cnt) as baseinfo_onloan_hit_mid
                from
                    dws.dws_loop_quota_while_list_his
                group by
                    1,
                    2
            ) b on a.mid = b.mid
            AND DATE (A.create_time) = date_add ('day', 1, b.data_date)
            left join (
                select
                    CID,
                    baseinfo_onloan_hit_mid
                from
                    (
                        SELECT
                            A.CID,
                            A.CREATE_TIME,
                            B.CREATE_TIME,
                            baseinfo_onloan_hit_mid,
                            row_number() over (
                                partition by
                                    cid
                                order by
                                    A.create_time
                            ) rn
                        FROM
                            (
                                SELECT
                                    cid,
                                    create_TIME,
                                    cast(
                                        json_extract (value, '$.baseinfo_onloan_hit_mid') as bigint
                                    ) as baseinfo_onloan_hit_mid
                                from
                                    ods.s09_os_variable_log
                                where
                                    name = 'baseinfo_onloan_hit_mid'
                                    and cid != 'null'
                            ) a
                            left join (
                                select
                                    create_time,
                                    biz_id
                                from
                                    ods.s05_creditx_order
                            ) b on A.cid = B.biz_id
                        where
                            A.create_TIME > B.create_time
                    )
                where
                    rn = 1
            ) C on a.ID = CAST(C.cid AS BIGINT)
            left join (
                select
                    CID,
                    baseinfo_m_onloan_hit_mid
                from
                    (
                        SELECT
                            A.CID,
                            A.CREATE_TIME,
                            B.CREATE_TIME,
                            baseinfo_m_onloan_hit_mid,
                            row_number() over (
                                partition by
                                    cid
                                order by
                                    A.create_time
                            ) rn
                        FROM
                            (
                                SELECT
                                    cid,
                                    create_TIME,
                                    cast(
                                        json_extract (value, '$.baseinfo_m_onloan_hit_mid') as bigint
                                    ) as baseinfo_m_onloan_hit_mid
                                from
                                    ods.s09_os_variable_log
                                where
                                    name = 'baseinfo_m_onloan_hit_mid'
                                    and cid != 'null'
                            ) a
                            left join (
                                select
                                    create_time,
                                    biz_id
                                from
                                    ods.s05_creditx_order
                            ) b on A.cid = B.biz_id
                        where
                            A.create_TIME > B.create_time
                    )
                where
                    rn = 1
            ) d on a.ID = CAST(d.cid AS BIGINT)
    ) T1
    LEFT JOIN (
        select
            a.id,
            count(b.biz_id) as mid_rn
        from
            ind.xly_reloan_num a
            left join (
                SELECT
                    biz_id,
                    mid,
                    create_time
                FROM
                    ods.s05_creditx_order
            ) b on a.mid = cast(b.mid as bigint)
            and a.create_time > b.create_time
        group by
            1
    ) T2 ON T1.ID = T2.id
    left join (
        select
            CID,
            CASE
                WHEN if_hit_white_list_phone > 0
                OR if_hit_white_list_identity > 0 THEN 1
                ELSE 0
            END AS if_hit_white_list
        FROM
            (
                SELECT
                    CID,
                    MAX(
                        CAST(
                            json_extract_scalar (value, '$.if_hit_white_list_phone') AS BIGINT
                        )
                    ) AS if_hit_white_list_phone,
                    MAX(
                        CAST(
                            json_extract_scalar (value, '$.if_hit_white_list_identity') AS BIGINT
                        )
                    ) AS if_hit_white_list_identity
                FROM
                    ods.s09_os_variable_log
                WHERE
                    name IN (
                        'if_hit_white_list_phone',
                        'if_hit_white_list_identity'
                    )
                    and cid != 'null'
                GROUP BY
                    1
            )
    ) t3 on T1.ID = cast(T3.CID as bigint);