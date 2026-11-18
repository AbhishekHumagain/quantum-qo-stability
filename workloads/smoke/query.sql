SELECT count(*)
FROM fact f, dim a, dim b, dim c, dim d
WHERE f.a=a.id AND f.b=b.id AND f.c=c.id AND f.d=d.id
  AND a.bucket<3 AND b.bucket<5 AND c.bucket<7;
