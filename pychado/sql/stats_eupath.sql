/*
 * This query returns the EuPathDB tags of all annotation updates since the latest release
 */
SELECT
	feature1.uniquename AS mrnaid,
	feature2.uniquename AS geneid,
	property1.value AS tag,
	feature1.organism_id AS orgid
FROM
	feature_cvterm fcvt																-- start off with a gene product (e.g. polypeptide)
	JOIN
	feature_cvtermprop property1 USING (feature_cvterm_id)							-- first property of the gene product
	JOIN
	feature_cvtermprop property2 USING (feature_cvterm_id)							-- second property of the gene product
	JOIN
	feature_relationship relation1 ON fcvt.feature_id = relation1.subject_id		-- connect gene product...
	JOIN
	feature feature1 ON relation1.object_id = feature1.feature_id					-- ... with transcript from which it derives
	JOIN
	feature_relationship relation2 ON relation2.subject_id = feature1.feature_id	-- connect transcript...
	JOIN
	feature feature2 ON relation2.object_id = feature2.feature_id					-- ... with the corresponding gene
WHERE
	property1.type_id IN (SELECT cvterm_id FROM cvterm WHERE name = 'qualifier')	-- qualifier must start with 'eupathdb'
	AND
	property1.value LIKE 'eupathdb_uc=%%'
	AND
	property2.type_id IN (SELECT cvterm_id FROM cvterm WHERE name = 'date')			-- capture any commits since the latest release
	AND
	property2.value > %s
	AND
	relation1.type_id IN (SELECT cvterm_id FROM cvterm WHERE name = 'derives_from')	-- gene product 'derives from' transcript
	AND
	feature1.organism_id IN (SELECT organism_id FROM organism WHERE {{CONDITION}})	-- a specific organism
ORDER BY
	mrnaid,
	tag,
	orgid
