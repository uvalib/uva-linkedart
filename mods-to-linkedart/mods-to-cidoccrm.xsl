<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:math="http://www.w3.org/2005/xpath-functions/math"
    xmlns:xpf="http://www.w3.org/2005/xpath-functions" xmlns:mods="http://www.loc.gov/mods/v3" xmlns:mods2la="https://linked.art/ns/v1/linked-art.json"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#" xmlns:xsd="http://www.w3.org/2001/XMLSchema#"
    xmlns:crm="http://www.cidoc-crm.org/cidoc-crm/" xmlns:la="https://linked.art/ns/terms/" xmlns:dig="http://www.ics.forth.gr/isl/CRMdig/"
    xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" exclude-result-prefixes="xsl xs math xpf mods mods2la" version="3.0">

    <xsl:output method="xml" encoding="UTF-8" indent="yes"/>

    <xsl:variable name="manifestBaseURL">https://s3.us-east-1.amazonaws.com/iiif-manifest-cache-production/pid-</xsl:variable>

    <xsl:variable name="resolver-url">http://127.0.0.1:8001/</xsl:variable>

    <xsl:variable name="resolver-on" as="xs:boolean">
        <xsl:value-of select="unparsed-text-available($resolver-url)"/>
    </xsl:variable>

    <xsl:variable name="roles" as="node()*">
        <xsl:copy-of select="document('roles.xml')"/>
    </xsl:variable>

    <xsl:template match="/">
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#" xmlns:xsd="http://www.w3.org/2001/XMLSchema#"
            xmlns:crm="http://www.cidoc-crm.org/cidoc-crm/">
            <xsl:apply-templates select="//mods:mods"/>
        </rdf:RDF>
    </xsl:template>

    <xsl:template match="mods:mods">

        <xsl:variable name="pid" select="mods:recordInfo/mods:recordIdentifier[@source = 'PID']"/>

        <xsl:variable name="typeOfResource">
            <xsl:choose>
                <xsl:when test="mods:relatedItem[@type = 'original']/mods:typeOfResource">
                    <xsl:value-of select="mods:relatedItem[@type = 'original']/mods:typeOfResource"/>
                </xsl:when>
                <xsl:when test="mods:typeOfResource">
                    <xsl:value-of select="mods:typeOfResource"/>
                </xsl:when>
            </xsl:choose>
        </xsl:variable>

        <xsl:variable name="information_object">
            <xsl:choose>
                <xsl:when test="$typeOfResource = 'still image' or $typeOfResource = 'moving image' or $typeOfResource = 'three dimensional object'">crm:E36_Visual_Item</xsl:when>
                <xsl:otherwise>crm:E33_Linguistic_Object</xsl:otherwise>
            </xsl:choose>
        </xsl:variable>


        <crm:E22_Human-Made_Object>
            <xsl:attribute name="rdf:about" select="concat('https://search.lib.virginia.edu/sources/images/items/', $pid)"/>
            <rdfs:label>
                <xsl:value-of select="mods2la:generateTitle(mods:titleInfo)"/>
            </rdfs:label>

            <xsl:apply-templates select="mods:titleInfo[not(@type)]"/>
            
            <xsl:apply-templates
                select="mods:relatedItem[@type = 'original']/mods:identifier[(@type = 'local' and contains(lower-case(@displayLabel), 'call number')) or @type = 'accession number']"
                mode="primary-identifier"/>

            <!-- HMO classification -->
            <xsl:choose>
                <xsl:when test="mods:relatedItem[@type = 'original']/mods:typeOfResource">
                    <xsl:apply-templates select="mods:relatedItem[@type = 'original']/mods:typeOfResource"/>
                </xsl:when>
                <xsl:when test="mods:typeOfResource">
                    <xsl:apply-templates select="mods:typeOfResource"/>
                </xsl:when>
            </xsl:choose>

            <xsl:apply-templates select="mods:genre[@authority and @valueURI] | mods:relatedItem[@type = 'original']/mods:genre[@authority and @valueURI]"/>

            <!-- HMO "carries" LinguisticObject or "shows" VisualItem -->
            <xsl:variable name="carrier_property" select="
                    if ($information_object = 'crm:E36_Visual_Item') then
                        'crm:P65_shows_visual_item'
                    else
                        'crm:P128_carries'"/>

            <xsl:element name="{$carrier_property}">
                <xsl:attribute name="rdf:resource" select="concat('https://curio.lib.virginia.edu/view/', $pid)"/>
            </xsl:element>

            <xsl:if test="$information_object = 'crm:E36_Visual_Item'">
                <xsl:call-template name="mods2la:statements">
                    <xsl:with-param name="information_object" select="$information_object"/>
                </xsl:call-template>
            </xsl:if>

            <!-- HMOs that have VisualItems (generally) were created by a Production event -->
            <xsl:if test="$information_object = 'crm:E36_Visual_Item'">
                <xsl:call-template name="mods2la:creation">
                    <xsl:with-param name="information_object" select="$information_object"/>
                </xsl:call-template>
            </xsl:if>

            <!-- physical description -->
            <!--<xsl:apply-templates select="mods:physicalDescription"/>-->



            <!-- textual statements -->
            <!--<xsl:apply-templates select="mods:abstract"/>
            <xsl:apply-templates select="mods:physicalDescription/mods:extent" mode="statement"/>-->

            <!-- collection -->


            <!--<xsl:if test="string($pid)">
                <xsl:call-template name="mods2la:images">
                    <xsl:with-param name="pid" select="$pid"/>
                </xsl:call-template>
            </xsl:if>-->

        </crm:E22_Human-Made_Object>
        <!-- end of HMO -->

        <!-- start of information carrier object -->
        <xsl:element name="{$information_object}">
            <xsl:attribute name="rdf:about" select="concat('https://curio.lib.virginia.edu/view/', $pid)"/>
            <rdfs:label>
                <xsl:value-of select="concat('Content of ', mods2la:generateTitle(mods:titleInfo))"/>
            </rdfs:label>
            
            <xsl:apply-templates select="mods:titleInfo[not(@type)]"/>
            
            <!-- descriptive statements and physical description applies to LinguisticObject -->
            <xsl:if test="$information_object = 'crm:E33_Linguistic_Object'">
                <xsl:call-template name="mods2la:statements">
                    <xsl:with-param name="information_object" select="$information_object"/>
                </xsl:call-template>
            </xsl:if>
            
            <!-- LinguisticObjects have a Creation event -->
            <xsl:if test="$information_object = 'crm:E33_Linguistic_Object'">
                <xsl:call-template name="mods2la:creation">
                    <xsl:with-param name="information_object" select="$information_object"/>
                </xsl:call-template>
            </xsl:if>

            <!-- General subject terms/aboutness, use mods:form conditional -->            
            <!-- a mods:subject with child level URIs will have individually addressable parts -->
            <xsl:apply-templates select="mods:subject[child::*[@valueURI]]"/>
            <!-- subjects that have top-level URIs with a single topic -->
            <xsl:apply-templates select="mods:subject[@authority = 'lcsh' and @valueURI][mods:topic]"/>
            <!-- TGN hierarchical geographic: structure like LCSH -->

            <!-- Geonames subject places -->
            <xsl:apply-templates select="mods:subject/mods:hierarchicalGeographic/*[starts-with(@valueURI, 'https://sws.geonames.org/')][last()]"/>

            <!-- associate images with IO -->
            <!--<xsl:if test="string($pid)">
                <xsl:call-template name="mods2la:images">
                    <xsl:with-param name="pid" select="$pid"/>
                </xsl:call-template>
            </xsl:if>-->
        </xsl:element>


        <!-- end of information carrier -->
    </xsl:template>

    <xsl:template match="mods:titleInfo">
        <crm:P1_is_identified_by>
            <crm:E33_E41_Linguistic_Appellation>
                <crm:P190_has_symbolic_content>
                    <xsl:value-of select="mods2la:generateTitle(self::node())"/>
                </crm:P190_has_symbolic_content>
                <crm:P2_has_type rdf:resource="http://vocab.getty.edu/aat/300404670"/>
            </crm:E33_E41_Linguistic_Appellation>
        </crm:P1_is_identified_by>
    </xsl:template>

    <xsl:template match="mods:identifier" mode="primary-identifier">
        <crm:P1_is_identified_by>
            <crm:E33_E41_Linguistic_Appellation>
                <crm:P190_has_symbolic_content>
                    <xsl:value-of select="."/>
                </crm:P190_has_symbolic_content>
                <xsl:choose>
                    <xsl:when test="@type = 'accession number'">
                        <crm:P2_has_type rdf:resource="http://vocab.getty.edu/aat/300312355"/>
                    </xsl:when>
                    <xsl:when test="contains(lower-case(@displayLabel), 'call number')">
                        <crm:P2_has_type rdf:resource="http://vocab.getty.edu/aat/300311706"/>
                    </xsl:when>
                </xsl:choose>

            </crm:E33_E41_Linguistic_Appellation>
        </crm:P1_is_identified_by>
    </xsl:template>


    <!-- classifications -->
    <xsl:template match="mods:genre[@valueURI]">
        <crm:P2_has_type rdf:resource="{@valueURI}"/>
    </xsl:template>

    <xsl:template match="mods:typeOfResource">
        <xsl:variable name="text" select="."/>

        <xsl:variable name="resourceType" as="node()">
            <xsl:call-template name="mods2la:typeOfResource">
                <xsl:with-param name="text" select="$text"/>
            </xsl:call-template>
        </xsl:variable>

        <crm:P2_has_type rdf:resource="{$resourceType/@valueURI}"/>
    </xsl:template>

    <xsl:template match="mods:abstract">
        <crm:P67i_is_referred_to_by>
            <crm:E33_Linguistic_Object>
                <crm:P190_has_symbolic_content>
                    <xsl:value-of select="normalize-space(.)"/>
                </crm:P190_has_symbolic_content>
                <crm:P2_has_type rdf:resource="http://vocab.getty.edu/aat/300435416"/>
            </crm:E33_Linguistic_Object>
        </crm:P67i_is_referred_to_by>
    </xsl:template>

    <xsl:template match="mods:relatedItem[@type = 'original']" mode="production">
        <xsl:param name="event-class"/>

        <xsl:apply-templates select="mods:originInfo"/>

        <xsl:call-template name="mods2la:creation-contributors">
            <xsl:with-param name="event-class" select="$event-class"/>
        </xsl:call-template>
    </xsl:template>

    <!-- production properties -->
    <xsl:template match="mods:originInfo">
        <xsl:param name="event-class"/>

        <!-- dates -->
        <xsl:if test="mods:dateCreated or mods:dateIssued">
            <xsl:call-template name="timespan"/>
        </xsl:if>

        <xsl:apply-templates select="mods:place/mods:placeTerm[@valueURI]" mode="production"/>
    </xsl:template>

    <xsl:template name="timespan">
        <xsl:variable name="value">
            <xsl:choose>
                <xsl:when test="mods:dateCreated[@point = 'start'] and mods:dateCreated[@point = 'end']">
                    <xsl:choose>
                        <xsl:when test="mods:dateCreated[@point = 'start' and @encoding = 'iso8601'] and mods:dateCreated[@point = 'end' and @encoding = 'iso8601']">
                            <xsl:value-of
                                select="concat(mods:dateCreated[@point = 'start' and @encoding = 'iso8601'], '/', mods:dateCreated[@point = 'end' and @encoding = 'iso8601'])"/>
                        </xsl:when>
                        <xsl:otherwise>
                            <xsl:value-of select="concat(mods:dateCreated[@point = 'start'], '/', mods:dateCreated[@point = 'end'])"/>
                        </xsl:otherwise>
                    </xsl:choose>
                </xsl:when>
                <xsl:when test="mods:dateIssued[@point = 'start'] and mods:dateIssued[@point = 'end']">
                    <xsl:choose>
                        <xsl:when test="mods:dateIssued[@point = 'start' and @encoding = 'iso8601'] and mods:dateIssued[@point = 'end' and @encoding = 'iso8601']">
                            <xsl:value-of
                                select="concat(mods:dateIssued[@point = 'start' and @encoding = 'iso8601'], '/', mods:dateIssued[@point = 'end' and @encoding = 'iso8601'])"/>
                        </xsl:when>
                        <xsl:otherwise>
                            <xsl:value-of select="concat(mods:dateIssued[@point = 'start'], '/', mods:dateIssued[@point = 'end'])"/>
                        </xsl:otherwise>
                    </xsl:choose>
                </xsl:when>
                <xsl:when test="mods:dateCreated[(@encoding = 'iso8601' or @encoding = 'edtf') and not(@point)]">
                    <xsl:value-of select="mods:dateCreated[@encoding = 'iso8601' or @encoding = 'edtf'][1]"/>
                </xsl:when>
                <xsl:when test="mods:dateIssued[@encoding = 'iso8601' or @encoding = 'edtf' and not(@point)]">
                    <xsl:value-of select="mods:dateIssued[@encoding = 'iso8601' or @encoding = 'edtf'][1]"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:choose>
                        <xsl:when test="mods:dateCreated">
                            <xsl:value-of select="mods:dateCreated[1]"/>
                        </xsl:when>
                        <xsl:when test="mods:dateIssued">
                            <xsl:value-of select="mods:dateIssued[1]"/>
                        </xsl:when>
                    </xsl:choose>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:variable>

        <xsl:if test="string($value)">
            <crm:P4_has_time-span>
                <crm:E52_Time-Span>
                    <rdfs:label>
                        <xsl:value-of select="$value"/>
                    </rdfs:label>

                    <xsl:variable name="dateRange" as="node()*">
                        <xsl:if test="$resolver-on">
                            <result>
                                <xsl:if test="unparsed-text-available(concat($resolver-url, 'parse?date=', encode-for-uri($value)))">
                                    <xsl:copy-of select="json-to-xml(unparsed-text(concat($resolver-url, 'parse?date=', encode-for-uri($value))))"/>
                                </xsl:if>
                            </result>
                        </xsl:if>
                    </xsl:variable>

                    <xsl:if test="$dateRange//xpf:string[@key = 'fromDate'] and $dateRange//xpf:string[@key = 'toDate']">
                        <crm:P82a_begin_of_the_begin rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">
                            <xsl:value-of select="concat($dateRange//xpf:string[@key = 'fromDate'], 'T00:00:00Z')"/>
                        </crm:P82a_begin_of_the_begin>
                        <crm:P82b_end_of_the_end rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">
                            <xsl:value-of select="concat($dateRange//xpf:string[@key = 'toDate'], 'T23:59:59Z')"/>
                        </crm:P82b_end_of_the_end>
                    </xsl:if>
                </crm:E52_Time-Span>
            </crm:P4_has_time-span>

        </xsl:if>
    </xsl:template>

    <xsl:template match="mods:placeTerm" mode="production">
        <crm:P7_took_place_at rdf:resource="{@valueURI}"/>
    </xsl:template>

    <!-- subjects 'about' -->
    <xsl:template match="mods:subject[child::*[@valueURI]]">
        <xsl:choose>
            <xsl:when test="count(*) = 1">
                <crm:P129_is_about rdf:resource="{*/@valueURI}"/>
            </xsl:when>
            <xsl:otherwise>
                <crm:P129_is_about>
                    <crm:E55_Type>
                        <rdfs:label>
                            <xsl:for-each select="*">
                                <xsl:choose>
                                    <xsl:when test="self::mods:name">
                                        <xsl:value-of select="string-join(mods:namePart, ' ')"/>
                                    </xsl:when>
                                    <xsl:otherwise>
                                        <xsl:value-of select="normalize-space(.)"/>
                                    </xsl:otherwise>
                                </xsl:choose>
                                <xsl:if test="not(position() = last())">
                                    <xsl:text>--</xsl:text>
                                </xsl:if>
                            </xsl:for-each>
                        </rdfs:label>
                        <xsl:if test="*[@valueURI]">
                            <crm:P94i_was_created_by>
                                <crm:E65_Creation>
                                    <xsl:apply-templates select="*[@valueURI]" mode="subject"/>
                                </crm:E65_Creation>
                            </crm:P94i_was_created_by>
                        </xsl:if>
                    </crm:E55_Type>
                </crm:P129_is_about>
            </xsl:otherwise>
        </xsl:choose>


    </xsl:template>

    <xsl:template match="*" mode="subject">
        <crm:P15_was_influenced_by rdf:resource="{@valueURI}"/>
    </xsl:template>

    <!-- geographic subjects -->
    <xsl:template match="mods:geographic | *[parent::mods:hierarchicalGeographic]">
        <crm:P129_is_about rdf:resource="{@valueURI}"/>
    </xsl:template>

    <!-- la:Set (collection) -->
    <xsl:template match="mods:relatedItem[@type = 'host' and lower-case(@displayLabel) = 'part of'][mods:location/mods:url]">
        <la:member_of rdf:resource="{mods:location/mods:url}"/>
    </xsl:template>

    <xsl:template match="mods:physicalDescription"> </xsl:template>

    <xsl:template match="mods:extent" mode="statement">
        <crm:P67i_is_referred_to_by>
            <crm:E33_Linguistic_Object>
                <crm:P190_has_symbolic_content>
                    <xsl:value-of select="."/>
                </crm:P190_has_symbolic_content>
                <crm:P2_has_type rdf:resource="http://vocab.getty.edu/aat/300435430"/>
            </crm:E33_Linguistic_Object>
        </crm:P67i_is_referred_to_by>
    </xsl:template>

    <!-- CUSTOM TEMPLATES -->
    <xsl:template name="mods2la:statements">
        <xsl:param name="information_object"/>
        
        <xsl:apply-templates select="mods:abstract"/>
        <xsl:choose>
            <xsl:when test="mods:relatedItem[@type = 'original']/mods:physicalDescription/mods:extent">
                <xsl:apply-templates select="mods:relatedItem[@type = 'original']/mods:physicalDescription/mods:extent" mode="statement"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:apply-templates select="mods:physicalDescription/mods:extent" mode="statement"/>
            </xsl:otherwise>
        </xsl:choose>
        
    </xsl:template>
    
    <xsl:template name="mods2la:creation">
        <xsl:param name="information_object"/>

        <xsl:if test="mods:name or mods:relatedItem[@type = 'original']/mods:name or mods:relatedItem[@type = 'original']/mods:originInfo or mods:originInfo">
            <!-- VisualItems like photographs were produced by a production event, but LinguisticObjects like book texts or maps have a creation event, as a book may have been produced by a different event than the content -->
            <xsl:variable name="event-property" select="
                    if (($information_object) = 'crm:E36_Visual_Item') then
                        'crm:P108i_was_produced_by'
                    else
                        'crm:P94i_was_created_by'"/>
            <xsl:variable name="event-class" select="
                    if (($information_object) = 'crm:E36_Visual_Item') then
                        'crm:E12_Production'
                    else
                        'crm:E65_Creation'"/>

            <xsl:element name="{$event-property}">
                <xsl:element name="{$event-class}">

                    <!-- accommodate differing originInfo, depending on MARC source or manual MODS -->
                    <xsl:choose>
                        <xsl:when test="mods:relatedItem[@type = 'original']/mods:originInfo or mods:relatedItem[@type = 'original']/mods:name">
                            <xsl:apply-templates select="mods:relatedItem[@type = 'original']" mode="production">
                                <xsl:with-param name="event-class" select="$event-class"/>
                            </xsl:apply-templates>
                        </xsl:when>
                        <xsl:otherwise>
                            <xsl:apply-templates select="mods:originInfo[1]">
                                <xsl:with-param name="event-class" select="$event-class"/>
                            </xsl:apply-templates>
                        </xsl:otherwise>
                    </xsl:choose>

                    <!-- include contributor links if there are not names in the original relatedItem -->
                    <xsl:if test="mods:name and not(mods:relatedItem[@type = 'original']/mods:name)">
                        <xsl:call-template name="mods2la:creation-contributors">
                            <xsl:with-param name="event-class" select="$event-class"/>
                        </xsl:call-template>
                    </xsl:if>
                </xsl:element>
            </xsl:element>
        </xsl:if>
    </xsl:template>

    <xsl:template name="mods2la:creation-contributors">
        <xsl:param name="event-class"/>


        <xsl:variable name="productionHasParts" as="xs:boolean">
            <xsl:choose>
                <xsl:when test="count(distinct-values(mods:name/mods:role/mods:roleTerm[@authority = 'marcrelator']/@valueURI)) &gt; 1 and count(mods:name) &gt; 1">
                    <xsl:value-of select="true()"/>
                </xsl:when>
                <xsl:when test="mods:name/mods:role/mods:roleTerm[@authority = 'marcrelator' and @valueURI] and mods:name[not(mods:role)]">
                    <xsl:value-of select="true()"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="false()"/>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:variable>

        <xsl:choose>
            <xsl:when test="$productionHasParts = true()">
                <xsl:for-each select="mods:name[@valueURI]">
                    <crm:P9_consists_of>
                        <xsl:element name="{$event-class}">
                            <xsl:variable name="property">
                                <xsl:choose>
                                    <xsl:when test="mods:role/mods:roleTerm[@authority = 'marcrelator' and @valueURI]">
                                        <xsl:variable name="uri" select="mods:role[1]/mods:roleTerm[@authority = 'marcrelator' and @valueURI][1]/@valueURI"/>
                                        
                                        <xsl:choose>
                                            <xsl:when test="string($roles//role[@marcrelator = $uri]/@property)">
                                                <xsl:value-of select="$roles//role[@marcrelator = $uri]/@property"/>
                                            </xsl:when>
                                            <xsl:otherwise>
                                                <xsl:text>carried_out_by</xsl:text>
                                            </xsl:otherwise>
                                        </xsl:choose>
                                    </xsl:when>
                                    <xsl:otherwise>
                                        <xsl:text>carried_out_by</xsl:text>
                                    </xsl:otherwise>
                                </xsl:choose>
                            </xsl:variable>

                            <xsl:element name="crm:{if ($property = 'carried_out_by') then 'P14_carried_out_by' else 'P15_was_influenced_by'}"
                                namespace="http://www.cidoc-crm.org/cidoc-crm/">
                                <xsl:attribute name="rdf:resource" select="@valueURI"/>
                            </xsl:element>

                            <xsl:for-each select="distinct-values(mods:role/mods:roleTerm[@authority = 'marcrelator']/@valueURI)">
                                <xsl:variable name="uri" select="."/>

                                <crm:P32_used_general_technique>
                                    <xsl:attribute name="rdf:resource" select="
                                            if ($roles//role[@marcrelator = $uri]/@technique) then
                                                $roles//role[@marcrelator = $uri]/@technique
                                            else
                                                $uri"/>

                                </crm:P32_used_general_technique>
                            </xsl:for-each>
                        </xsl:element>
                    </crm:P9_consists_of>
                </xsl:for-each>
            </xsl:when>
            <xsl:otherwise>
                <xsl:for-each select="mods:name[@valueURI]">
                    <xsl:variable name="property">
                        <xsl:choose>
                            <xsl:when test="mods:role/mods:roleTerm[@authority = 'marcrelator' and @valueURI]">
                                <xsl:variable name="uri" select="mods:role[1]/mods:roleTerm[@authority = 'marcrelator' and @valueURI][1]/@valueURI"/>
                                
                                <xsl:choose>
                                    <xsl:when test="string($roles//role[@marcrelator = $uri]/@property)">
                                        <xsl:value-of select="$roles//role[@marcrelator = $uri]/@property"/>
                                    </xsl:when>
                                    <xsl:otherwise>
                                        <xsl:text>carried_out_by</xsl:text>
                                    </xsl:otherwise>
                                </xsl:choose>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:text>carried_out_by</xsl:text>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:variable>

                    <xsl:if test="not($property = 'provenance')">
                        <xsl:element name="crm:{if ($property = 'carried_out_by') then 'P14_carried_out_by' else 'P15_was_influenced_by'}"
                            namespace="http://www.cidoc-crm.org/cidoc-crm/">
                            <xsl:attribute name="rdf:resource" select="@valueURI"/>
                        </xsl:element>

                        <xsl:for-each select="distinct-values(mods:role/mods:roleTerm[@authority = 'marcrelator']/@valueURI)">
                            <xsl:variable name="uri" select="."/>

                            <crm:P32_used_general_technique>
                                <xsl:attribute name="rdf:resource" select="
                                        if ($roles//role[@marcrelator = $uri]/@technique) then
                                            $roles//role[@marcrelator = $uri]/@technique
                                        else
                                            $uri"/>
                            </crm:P32_used_general_technique>
                        </xsl:for-each>
                    </xsl:if>
                </xsl:for-each>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template name="mods2la:images">
        <xsl:param name="pid"/>

        <!-- get exemplar PID IIIF image from API -->
        <xsl:variable name="manifest-uri" select="concat($manifestBaseURL, replace($pid, ':', '-'))"/>

        <xsl:variable name="response">
            <xsl:if test="unparsed-text-available($manifest-uri)">
                <xsl:copy-of select="json-to-xml(unparsed-text($manifest-uri))"/>
            </xsl:if>
        </xsl:variable>

        <xsl:variable name="thumbnail-uri" select="$response/xpf:map/xpf:map[@key = 'thumbnail']/xpf:string[@key = '@id']"/>

        <crm:P129i_is_subject_of>
            <crm:E33_Linguistic_Object>
                <la:digitally_carried_by>
                    <dig:D1_Digital_Object>
                        <la:access_point rdf:resource="{$manifest-uri}"/>
                        <dc:format>application/ld+json;profile='http://iiif.io/api/presentation/2/context.json'</dc:format>
                        <dcterms:conformsTo rdf:resource="http://iiif.io/api/presentation/2/context.json"/>
                    </dig:D1_Digital_Object>
                </la:digitally_carried_by>
            </crm:E33_Linguistic_Object>
        </crm:P129i_is_subject_of>
        <crm:P138i_has_representation>
            <crm:VisualItem>
                <la:digitally_shown_by>
                    <dig:D1_Digital_Object>
                        <rdfs:label>Primary Image Thumbnail</rdfs:label>
                        <crm:P2_has_type rdf:resource="http://vocab.getty.edu/aat/300215302"/>
                        <dc:format>image/jpeg</dc:format>
                        <la:access_point rdf:resource="{$thumbnail-uri}"/>
                    </dig:D1_Digital_Object>
                </la:digitally_shown_by>
            </crm:VisualItem>
        </crm:P138i_has_representation>
    </xsl:template>

    <xsl:template name="mods2la:typeOfResource">
        <xsl:param name="text"/>

        <xsl:choose>
            <xsl:when test="$text = 'text'">
                <type>
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300263751</xsl:attribute>
                    <xsl:text>texts (documents)</xsl:text>
                </type>
            </xsl:when>
            <xsl:when test="$text = 'cartographic'">
                <type>
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300028052</xsl:attribute>
                    <xsl:text>cartographic materials</xsl:text>
                </type>
            </xsl:when>
            <xsl:when test="$text = 'notated music'">
                <type>
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300417622</xsl:attribute>
                    <xsl:text>musical notation</xsl:text>
                </type>
            </xsl:when>
            <xsl:when test="$text = 'sound recording-nonmusical'">
                <type>
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300028633</xsl:attribute>
                    <xsl:text>sound recordings</xsl:text>
                </type>
            </xsl:when>
            <xsl:when test="$text = 'sound recording-musical'">
                <type>
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300028633</xsl:attribute>
                    <xsl:text>sound recordings</xsl:text>
                </type>
            </xsl:when>
            <xsl:when test="$text = 'still image'">
                <type>
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300264387</xsl:attribute>
                    <xsl:text>images (object genre)</xsl:text>
                </type>
            </xsl:when>
            <xsl:when test="$text = 'moving image'">
                <type>
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300263857</xsl:attribute>
                    <xsl:text>moving images</xsl:text>
                </type>
            </xsl:when>
            <xsl:when test="$text = 'three dimensional object'">
                <type>
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300117127</xsl:attribute>
                    <xsl:text>artifacts (object genre)</xsl:text>
                </type>
            </xsl:when>
            <xsl:when test="$text = 'software, multimedia'">
                <type>
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300028566</xsl:attribute>
                    <xsl:text>software</xsl:text>
                </type>
            </xsl:when>
            <xsl:when test="$text = 'mixed material'">
                <type>
                    <xsl:attribute name="valueURI">http://vocab.getty.edu/aat/300404821</xsl:attribute>
                    <xsl:text>multiple materials (materials for groups)</xsl:text>
                </type>
            </xsl:when>
            <xsl:otherwise>
                <type>
                    <xsl:value-of select="."/>
                </type>
            </xsl:otherwise>
        </xsl:choose>

    </xsl:template>

    <!-- FUNCTIONS -->
    <xsl:function name="mods2la:generateTitle">
        <xsl:param name="titleInfo"/>

        <xsl:value-of select="normalize-space($titleInfo/mods:title)"/>
        <xsl:if test="$titleInfo/mods:subTitle">
            <xsl:text>: </xsl:text>
            <xsl:value-of select="normalize-space($titleInfo/mods:subTitle)"/>
        </xsl:if>
    </xsl:function>

</xsl:stylesheet>
