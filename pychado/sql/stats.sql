/*
 * This query returns all changes in annotation/gene model since the latest release for a given organism
 */
SELECT
	feature1.uniquename AS mrnaid,
	feature2.uniquename AS geneid,
	fcvt.feature_cvterm_id AS annotationid,
	property1.value AS annotationvalue,
	property1.type_id
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
	fcvt.cvterm_id IN (SELECT cvterm_id FROM cvterm JOIN cv USING (cv_id) WHERE cv.name = 'annotation_change')		-- capture all changes in annotation
	AND
	property1.type_id IN (SELECT cvterm_id FROM cvterm WHERE name = 'qualifier' OR name = 'date')	-- get annotation description or date
	AND
	property2.type_id IN (SELECT cvterm_id FROM cvterm WHERE name = 'date')			-- capture any commits since the latest release
	AND
	property2.value > '20180227'
	AND
	relation1.type_id IN (SELECT cvterm_id FROM cvterm WHERE name = 'derives_from')	-- gene product 'derives from' transcript
	AND
	feature1.organism_id IN (SELECT organism_id FROM organism WHERE {{CONDITION}})	-- a specific organism
ORDER BY
	feature2.uniquename,
	fcvt.feature_cvterm_id,
	property1.type_id,
	property1.value
