with expected(rating_code) as (values ('F0'),('F1'),('F2'),('F3'),('F4'),('F5'),('EF0'),('EF1'),('EF2'),('EF3'),('EF4'),('EF5'),('Unknown'))
select expected.rating_code from expected left join {{ ref('dim_tornado_intensities') }} using (rating_code)
where dim_tornado_intensities.rating_code is null
