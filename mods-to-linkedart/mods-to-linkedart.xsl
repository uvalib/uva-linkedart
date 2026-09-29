<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:math="http://www.w3.org/2005/xpath-functions/math"
    xmlns:xpf="http://www.w3.org/2005/xpath-functions" xmlns:numishare="https://github.com/ewg118/numishare" xmlns:mods="http://www.loc.gov/mods/v3"
    xmlns:mods2la="https://linked.art/ns/v1/linked-art.json" exclude-result-prefixes="#all" version="3.0">

    <xsl:include href="json-metamodel.xsl"/>

    <xsl:output method="text" encoding="UTF-8" indent="yes"/>

    <xsl:variable name="manifestBaseURL">https://s3.us-east-1.amazonaws.com/iiif-manifest-cache-production/pid-</xsl:variable>

    <xsl:variable name="resolver-url">http://127.0.0.1:8001/</xsl:variable>

    <xsl:variable name="resolver-on" as="xs:boolean">
        <xsl:value-of select="unparsed-text-available($resolver-url)"/>
    </xsl:variable>

    <xsl:variable name="roles" as="node()*">
        <xsl:copy-of select="document('roles.xml')"/>
    </xsl:variable>

    <xsl:template match="/">
        <xsl:variable name="model" as="item()*">
            <_array>
                <xsl:apply-templates select="mods:modsCollection | mods:mods"/>
            </_array>
        </xsl:variable>

        <xsl:apply-templates select="$model"/>

        <!-- <xsl:copy-of select="$model"/>-->

    </xsl:template>

    <xsl:template match="mods:modsCollection">
        <xsl:apply-templates select="//mods:mods"/>
    </xsl:template>

    <xsl:template match="mods:mods">

        <xsl:variable name="pid" select="mods:recordInfo/mods:recordIdentifier[@source = 'PID']"/>
        
        <xsl:variable name="typeOfResource">
            <xsl:choose>
                <xsl:when test="mods:relatedItem[@type = 'original']/mods:typeOfResource">
                    <xsl:value-of select="mods:relatedItem[@type='original']/mods:typeOfResource"/>
                </xsl:when>
                <xsl:when test="mods:typeOfResource">
                    <xsl:value-of select="mods:typeOfResource"/>
                </xsl:when>                
            </xsl:choose>
        </xsl:variable>
        
        <xsl:variable name="information_object">
            <xsl:choose>
                <xsl:when test="$typeOfResource = 'still image' or $typeOfResource = 'moving image' or $typeOfResource = 'three dimensional object'">VisualItem</xsl:when>
                <xsl:otherwise>LinguisticObject</xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        
        <!-- HMO -->
        <_object>
            <__context>https://linked.art/ns/v1/linked-art.json</__context>
            <id>
                <xsl:value-of select="concat('https://search.lib.virginia.edu/sources/images/items/', $pid)"/>
            </id>
            <type>HumanMadeObject</type>
            <_label>
                <xsl:value-of select="mods2la:generateTitle(mods:titleInfo)"/>
            </_label>

            <identified_by>
                <_array>
                    <xsl:apply-templates select="mods:titleInfo[not(@type)]"/>
                    <xsl:apply-templates select="mods:relatedItem[@type = 'original']/mods:identifier[@type = 'local']"/>
                </_array>
            </identified_by>

            <!-- Type of Work -->
            <xsl:if test="mods:genre[@authority and @valueURI] or mods:typeOfResource or mods:relatedItem[@type='original']/mods:typeOfResource or mods:relatedItem[@type = 'original']/mods:genre[@authority and @valueURI]">
                <classified_as>
                    <_array>
                        
                        <!-- broad classifications derived from LC resource types; examine mods:relatedItem[@type = 'original'] first -->
                        <xsl:choose>
                            <xsl:when test="mods:relatedItem[@type = 'original']/mods:typeOfResource">
                                <xsl:apply-templates select="mods:relatedItem[@type='original']/mods:typeOfResource"/>
                            </xsl:when>
                            <xsl:when test="mods:typeOfResource">
                                <xsl:apply-templates select="mods:typeOfResource"/>
                            </xsl:when>                
                        </xsl:choose>        
                        
                        <!-- genres -->
                        <xsl:apply-templates select="mods:genre[@authority and @valueURI] | mods:relatedItem[@type = 'original']/mods:genre[@authority and @valueURI]"/>
                    </_array>
                </classified_as>
            </xsl:if>
            
            <!-- physical materials -->
            <xsl:if test="mods:relatedItem[@type = 'original']/mods:physicalDescription/mods:form[@type = 'material' and @valueURI] or mods:physicalDescription/mods:form[@type = 'material' and @valueURI]">
                <made_of>
                    <_array>
                        <xsl:apply-templates select="mods:relatedItem[@type = 'original']/mods:physicalDescription/mods:form[@type = 'material' and @valueURI] | mods:physicalDescription/mods:form[@type = 'material' and @valueURI]"/>
                    </_array>
                </made_of>
            </xsl:if>

            <!-- HMO "carries" LinguisticObject or "shows" VisualItem -->
            <xsl:variable name="carrier_property" select="if ($information_object = 'VisualItem') then 'shows' else 'carries'"/>
            
            <xsl:element name="{$carrier_property}">
                <_array>
                    <_object>
                        <id>
                            <xsl:value-of select="concat('https://curio.lib.virginia.edu/view/', $pid)"/>
                        </id>
                        <type>
                            <xsl:value-of select="$information_object"/>
                        </type>
                        <_label>
                            <xsl:value-of select="concat('Content of ', mods2la:generateTitle(mods:titleInfo))"/>
                        </_label>
                    </_object>
                </_array>
            </xsl:element>
            
            <!-- HMOs that have VisualItems (generally) were created by a Production event -->
            <xsl:if test="$information_object = 'VisualItem'">
                <xsl:call-template name="mods2la:creation">
                    <xsl:with-param name="information_object" select="$information_object"/>
                </xsl:call-template>
            </xsl:if>

            <!-- abstract -->
            <xsl:if test="$information_object = 'VisualItem'">
                <xsl:call-template name="mods2la:statements">
                    <xsl:with-param name="information_object" select="$information_object"/>
                </xsl:call-template>
            </xsl:if>

            <!-- collection -->
            <xsl:if test="mods:relatedItem[@type = 'host' and lower-case(@displayLabel) = 'part of'][mods:location/mods:url]">
                <member_of>
                    <_array>
                        <xsl:apply-templates select="mods:relatedItem[@type = 'host' and lower-case(@displayLabel) = 'part of'][mods:location/mods:url]"/>
                    </_array>
                </member_of>
            </xsl:if>

            <xsl:if test="string($pid)">
                <xsl:call-template name="mods2la:images">
                    <xsl:with-param name="pid" select="$pid"/>
                </xsl:call-template>
            </xsl:if>
        </_object>
        <!-- end of HMO -->
        
        <!-- Use Curio URI as digital InformationObject -->
        <_object>
            <__context>https://linked.art/ns/v1/linked-art.json</__context>
            <id>
                <xsl:value-of select="concat('https://curio.lib.virginia.edu/view/', $pid)"/>
            </id>
            <type>
                <xsl:value-of select="$information_object"/>
            </type>
            <_label>
                <xsl:value-of select="concat('Content of ', mods2la:generateTitle(mods:titleInfo))"/>
            </_label>
            
            <identified_by>
                <_array>
                    <xsl:apply-templates select="mods:titleInfo[not(@type)]"/>
                    <xsl:apply-templates select="mods:relatedItem[@type = 'original']/mods:identifier[@type = 'local']"/>
                </_array>
            </identified_by>
            
            <!-- descriptive statements and physical description applies to LinguisticObject -->
            <xsl:if test="$information_object = 'LinguisticObject'">
                <xsl:call-template name="mods2la:statements">
                    <xsl:with-param name="information_object" select="$information_object"/>
                </xsl:call-template>
            </xsl:if>
            
            <!-- LinguisticObjects have Creation events -->
            <xsl:if test="$information_object = 'LinguisticObject'">
                <xsl:call-template name="mods2la:creation">
                    <xsl:with-param name="information_object" select="$information_object"/>
                </xsl:call-template>
            </xsl:if>
            
            <!-- subjects -->
            <xsl:if
                test="mods:subject[@authority = 'lcsh' and child::*[@valueURI]] or mods:subject[@authority = 'lcsh' and @valueURI][mods:topic] or mods:subject[mods:hierarchicalGeographic/*[starts-with(@valueURI, 'https://sws.geonames.org/')]] or mods:subject[@authority = 'tgn']/descendant::*[@valueURI]">
                
                <xsl:variable name="subject_property" select="if ($information_object = 'VisualItem') then 'represents' else 'about'"/>
                
                <xsl:element name="{$subject_property}">
                    <_array>
                        <!-- a mods:subject with child level URIs will have individually addressable parts -->
                        <xsl:apply-templates select="mods:subject[@authority = 'lcsh' and child::*[@valueURI]]"/>
                        <!-- subjects that have top-level URIs with a single topic -->
                        <xsl:apply-templates select="mods:subject[@authority = 'lcsh' and @valueURI][mods:topic]"/>
                        
                        <!-- TGN or Geonames subject places -->
                        <xsl:apply-templates select="mods:subject/mods:hierarchicalGeographic/*[starts-with(@valueURI, 'https://sws.geonames.org/')]"/>
                        <xsl:apply-templates select="mods:subject[@authority = 'tgn']/descendant::*[@valueURI]"/>
                    </_array>
                </xsl:element>     
                
                <!-- associate images with IO -->
                <xsl:if test="string($pid)">
                    <xsl:call-template name="mods2la:images">
                        <xsl:with-param name="pid" select="$pid"/>
                    </xsl:call-template>
                </xsl:if>
            </xsl:if>
        </_object>
        <!-- end of InformationObject -->
    </xsl:template>

    <!-- titles and identifiers -->
    <xsl:template match="mods:titleInfo">
        <_object>
            <type>Name</type>
            <content>
                <xsl:value-of select="mods2la:generateTitle(.)"/>
            </content>
            <classified_as>
                <_array>
                    <_object>
                        <id>http://vocab.getty.edu/aat/300404670</id>
                        <_label>preferred forms</_label>
                        <type>Type</type>
                    </_object>
                </_array>
            </classified_as>
        </_object>
    </xsl:template>

    <xsl:template match="mods:identifier[@type = 'local']">
        <xsl:if test="contains(lower-case(@displayLabel), 'call number')">
            <_object>
                <type>Identifier</type>
                <content>
                    <xsl:value-of select="."/>
                </content>
                <classified_as>
                    <_array>
                        <_object>
                            <id>http://vocab.getty.edu/aat/300311706</id>
                            <_label>call numbers</_label>
                            <type>Type</type>
                        </_object>
                    </_array>
                </classified_as>
            </_object>
        </xsl:if>
    </xsl:template>

    <!-- classifications -->
    <xsl:template match="mods:typeOfResource">
        <xsl:variable name="text" select="."/>
        
        <xsl:variable name="resourceType" as="node()">
            <xsl:call-template name="mods2la:typeOfResource">
                <xsl:with-param name="text" select="$text"/>
            </xsl:call-template>
        </xsl:variable>
        
        <!-- only include the type of work if it resolves to an AAT URI -->
        <xsl:if test="$resourceType/@valueURI">
            <_object>
                <id>
                    <xsl:value-of select="$resourceType/@valueURI"/>
                </id>
                <type>Type</type>
                <_label>
                    <xsl:value-of select="$resourceType"/>
                </_label>
                <classified_as>
                    <_array>
                        <_object>
                            <id>http://vocab.getty.edu/aat/300435443</id>
                            <type>Type</type>
                            <_label>Type of Work</_label>
                        </_object>
                    </_array>
                </classified_as>
            </_object>
        </xsl:if>
    </xsl:template>

    <xsl:template match="mods:genre">
        <_object>
            <xsl:if test="@valueURI">
                <id>
                    <xsl:value-of select="@valueURI"/>
                </id>
            </xsl:if>
            <type>Type</type>
            <_label>
                <xsl:value-of select="."/>
            </_label>
            <classified_as>
                <_array>
                    <_object>
                        <id>http://vocab.getty.edu/aat/300435443</id>
                        <type>Type</type>
                        <_label>Type of Work</_label>
                    </_object>
                </_array>
            </classified_as>
        </_object>
    </xsl:template>
    
    <xsl:template match="mods:form[@type = 'material' and @valueURI]">
        <_object>
            <id>
                <xsl:value-of select="@valueURI"/>
            </id>
            <type>Material</type>
            <_label>
                <xsl:value-of select="."/>
            </_label>
        </_object>
    </xsl:template>

    <xsl:template match="mods:abstract">
        <_object>
            <type>LinguisticObject</type>
            <content>
                <xsl:value-of select="."/>
            </content>
            <classified_as>
                <_array>
                    <_object>
                        <id>http://vocab.getty.edu/aat/300435416</id>
                        <type>Type</type>
                        <_label>Description</_label>
                        <classified_as>
                            <_array>
                                <_object>
                                    <id>http://vocab.getty.edu/aat/300418049</id>
                                    <type>Type</type>
                                    <_label>Brief Text</_label>
                                </_object>
                            </_array>
                        </classified_as>
                    </_object>
                </_array>
            </classified_as>
        </_object>
    </xsl:template>

    <!-- production properties -->
    <xsl:template match="mods:relatedItem[@type = 'original']" mode="production">
        <xsl:param name="event-class"/>
        
        <xsl:apply-templates select="mods:originInfo"/>
        
        <xsl:call-template name="mods2la:creation-contributors">
            <xsl:with-param name="event-class" select="$event-class"/>
        </xsl:call-template>
    </xsl:template>
    
    <xsl:template match="mods:originInfo">
        <xsl:param name="event-class"/>

        <!-- dates -->
        <xsl:if test="mods:dateCreated or mods:dateIssued">
            <xsl:call-template name="timespan"/>
        </xsl:if>

        <xsl:if test="mods:place/mods:placeTerm[@valueURI]">
            <took_place_at>
                <_array>
                    <xsl:apply-templates select="mods:place/mods:placeTerm[@valueURI]" mode="production"/>
                </_array>
            </took_place_at>
        </xsl:if>
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
            <timespan>
                <_object>
                    <type>TimeSpan</type>
                    <_label>
                        <xsl:value-of select="$value"/>
                    </_label>

                    <xsl:variable name="dateRange" as="node()*">
                        <xsl:if test="$resolver-on">
                            <xsl:copy-of select="json-to-xml(unparsed-text(concat($resolver-url, 'parse?date=', encode-for-uri($value))))"/>
                        </xsl:if>
                    </xsl:variable>

                    <xsl:if test="$dateRange/xpf:map/*">
                        <begin_of_the_begin>
                            <xsl:value-of select="concat($dateRange/xpf:map/xpf:string[@key = 'fromDate'], 'T00:00:00Z')"/>
                        </begin_of_the_begin>
                        <end_of_the_end>
                            <xsl:value-of select="concat($dateRange/xpf:map/xpf:string[@key = 'toDate'], 'T23:59:59Z')"/>
                        </end_of_the_end>
                    </xsl:if>
                </_object>
            </timespan>
        </xsl:if>
    </xsl:template>

    <xsl:template match="mods:placeTerm" mode="production">
        <_object>
            <id>
                <xsl:value-of select="@valueURI"/>
            </id>
            <type>Place</type>
            <_label>
                <xsl:value-of select="."/>
            </_label>
        </_object>
    </xsl:template>

    <xsl:template match="mods:name" mode="production">
        <_object>
            <xsl:if test="@valueURI">
                <id>
                    <xsl:value-of select="@valueURI"/>
                </id>
            </xsl:if>
            <type>
                <xsl:value-of select="
                        if (@type = 'personal') then
                            'Person'
                        else
                            'Group'"/>
            </type>
            <_label>
                <xsl:choose>
                    <xsl:when test="count(mods:namePart) = 1">
                        <xsl:value-of select="mods:namePart"/>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:choose>
                            <xsl:when test="mods:namePart[@type = 'family'] and mods:namePart[@type = 'given']">
                                <xsl:value-of select="mods:namePart[@type = 'family']"/>
                                <xsl:text>, </xsl:text>
                                <xsl:value-of select="mods:namePart[@type = 'given']"/>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:value-of select="mods:namePart[not(@type)]"/>
                            </xsl:otherwise>
                        </xsl:choose>
                        <xsl:if test="mods:namePart[@type = 'date']">
                            <xsl:choose>
                                <xsl:when test="ends-with(mods:namePart[@type = 'date']/preceding-sibling::mods:namePart[1], ',')">
                                    <xsl:text> </xsl:text>
                                </xsl:when>
                                <xsl:otherwise>
                                    <xsl:text>, </xsl:text>
                                </xsl:otherwise>
                            </xsl:choose>

                            <xsl:value-of select="mods:namePart[@type = 'date']"/>
                        </xsl:if>
                    </xsl:otherwise>
                </xsl:choose>
            </_label>
        </_object>
    </xsl:template>

    <!-- VisualItems -->
    <xsl:template match="mods:subject[@valueURI][mods:topic]">
        <_object>
            <id>
                <xsl:value-of select="@valueURI"/>
            </id>
            <type>Type</type>
            <_label>
                <xsl:value-of select="string-join(*, '--')"/>
            </_label>
        </_object>
    </xsl:template>

    <xsl:template match="mods:subject[@authority = 'lcsh' and child::*[@valueURI]]">
        <_object>
            <type>Type</type>
            <_label>
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
            </_label>
            <xsl:if test="*[@valueURI]">
                <created_by>
                    <_object>
                        <type>Creation</type>
                        <influenced_by>
                            <_array>
                                <xsl:apply-templates select="*[@valueURI]" mode="subject"/>
                            </_array>
                        </influenced_by>
                    </_object>
                </created_by>
            </xsl:if>
        </_object>
    </xsl:template>

    <xsl:template match="*" mode="subject">
        <_object>
            <id>
                <xsl:value-of select="@valueURI"/>
            </id>
            <type>Type</type>
            <_label>
                <xsl:choose>
                    <xsl:when test="self::mods:name">
                        <xsl:value-of select="string-join(mods:namePart, ' ')"/>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:value-of select="normalize-space(.)"/>
                    </xsl:otherwise>
                </xsl:choose>
            </_label>
        </_object>
    </xsl:template>

    <!-- geographic subjects -->
    <xsl:template match="mods:geographic | *[parent::mods:hierarchicalGeographic]">
        <_object>
            <id>
                <xsl:value-of select="@valueURI"/>
            </id>
            <type>Place</type>
            <_label>
                <xsl:value-of select="."/>
            </_label>
        </_object>
    </xsl:template>

    <!-- la:Set (collection) -->
    <xsl:template match="mods:relatedItem[@type = 'host' and lower-case(@displayLabel) = 'part of'][mods:location/mods:url]">
        <_object>
            <id>
                <xsl:value-of select="mods:location/mods:url"/>
            </id>
            <type>Set</type>
            <_label>
                <xsl:value-of select="mods2la:generateTitle(mods:titleInfo)"/>
            </_label>
        </_object>
    </xsl:template>

    <xsl:template match="mods:extent" mode="statement">
        <_object>
            <type>LinguisticObject</type>
            <content>
                <xsl:value-of select="normalize-space(.)"/>
            </content>
            <classified_as>
                <_array>
                    <_object>
                        <id>http://vocab.getty.edu/aat/300435430</id>
                        <type>Type</type>
                        <_label>Dimension Statement</_label>
                        <classifed_as>
                            <_array>
                                <_object>
                                    <id>http://vocab.getty.edu/aat/300418049</id>
                                    <type>Type</type>
                                    <_label>Brief Text</_label>
                                </_object>
                            </_array>
                        </classifed_as>
                    </_object>
                </_array>
            </classified_as>
        </_object>
    </xsl:template>
    
    <!-- TEMPLATES -->
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
        
        <subject_of>
            <_array>
                <_object>
                    <type>LinguisticObject</type>
                    <digitally_carried_by>
                        <_array>
                            <_object>
                                <type>DigitalObject</type>
                                <_label>IIIF v2 Manifest</_label>
                                <access_point>
                                    <_array>
                                        <_object>
                                            <id>
                                                <xsl:value-of select="$manifest-uri"/>
                                            </id>
                                            <type>DigitalObject</type>
                                        </_object>
                                    </_array>
                                </access_point>
                                <conforms_to>
                                    <_array>
                                        <_object>
                                            <id>http://iiif.io/api/presentation/2/context.json</id>
                                            <type>InformationObject</type>
                                        </_object>
                                    </_array>
                                </conforms_to>
                                <format>application/ld+json;profile='http://iiif.io/api/presentation/2/context.json'</format>
                            </_object>
                        </_array>
                    </digitally_carried_by>
                </_object>
            </_array>
        </subject_of>
        
        <representation>
            <_array>
                <_object>
                    <type>VisualItem</type>
                    <digitally_shown_by>
                        <_array>
                            <_object>
                                <type>DigitalObject</type>
                                <_label>Primary Image Thumbnail</_label>
                                <classified_as>
                                    <_array>
                                        <_object>
                                            <id>http://vocab.getty.edu/aat/300215302</id>
                                            <type>Type</type>
                                            <_label>Digital Image</_label>
                                        </_object>
                                    </_array>
                                </classified_as>
                                <format>image/jpeg</format>
                                <access_point>
                                    <_array>
                                        <_object>
                                            <id>
                                                <xsl:value-of select="$thumbnail-uri"/>
                                            </id>
                                            <type>DigitalObject</type>
                                        </_object>
                                    </_array>
                                </access_point>
                            </_object>
                        </_array>
                    </digitally_shown_by>
                </_object>
            </_array>
        </representation>
    </xsl:template>
    
    <xsl:template name="mods2la:statements">
        <xsl:param name="information_object"/>
        
        <xsl:if test="mods:abstract or mods:physicalDescription/mods:extent or mods:relatedItem[@type = 'original']/mods:physicalDescription/mods:extent">
            <referred_to_by>
                <_array>
                    <xsl:apply-templates select="mods:abstract"/>
                    <xsl:choose>
                        <xsl:when test="mods:relatedItem[@type = 'original']/mods:physicalDescription/mods:extent">
                            <xsl:apply-templates select="mods:relatedItem[@type = 'original']/mods:physicalDescription/mods:extent" mode="statement"/>
                        </xsl:when>
                        <xsl:otherwise>
                            <xsl:apply-templates select="mods:physicalDescription/mods:extent" mode="statement"/>
                        </xsl:otherwise>
                    </xsl:choose>
                    
                </_array>
            </referred_to_by>
        </xsl:if>
    </xsl:template>
    
    <xsl:template name="mods2la:creation">
        <xsl:param name="information_object"/>
        
        <xsl:if test="mods:name or mods:relatedItem[@type = 'original']/mods:name or mods:relatedItem[@type = 'original']/mods:originInfo or mods:originInfo">
            <xsl:variable name="event-property" select="
                if (($information_object) = 'VisualItem') then
                'produced_by'
                else
                'created_by'"/>
            <xsl:variable name="event-class" select="
                if (($information_object) = 'VisualItem') then
                'Production'
                else
                'Creation'"/>
            
            <xsl:element name="{$event-property}">
                <_object>
                    <type>
                        <xsl:value-of select="$event-class"/>
                    </type>
                    
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
                </_object>
            </xsl:element>
        </xsl:if>
    </xsl:template>
    
    <xsl:template name="mods2la:creation-contributors">
        <xsl:param name="event-class"/>
        
        <!-- if more than one role is reported among the name(s), then split the production activity into parts: evaluate on various conditionals -->
        <xsl:variable name="productionHasParts" as="xs:boolean">
            <xsl:choose>
                <xsl:when
                    test="count(distinct-values(mods:name/mods:role/mods:roleTerm[@authority = 'marcrelator']/@valueURI)) &gt; 1 and count(mods:name) &gt; 1">
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
                <part>
                    <_array>
                        <xsl:for-each select="mods:name">
                            <xsl:variable name="property">
                                <xsl:choose>
                                    <xsl:when test="mods:role/mods:roleTerm[@authority = 'marcrelator' and @valueURI]">
                                        <xsl:variable name="uri" select="mods:role[1]/mods:roleTerm[@authority = 'marcrelator' and @valueURI][1]/@valueURI"/>
                                        
                                        <xsl:value-of select="$roles//role[@marcrelator = $uri]/@property"/>
                                    </xsl:when>
                                    <xsl:otherwise>
                                        <xsl:text>carried_out_by</xsl:text>
                                    </xsl:otherwise>
                                </xsl:choose>
                            </xsl:variable>
                            
                            <!-- ignore names that should be considered under the provenance section, not related to production -->
                            <xsl:if test="not($property = 'provenance')">
                                <_object>
                                    <type>
                                        <xsl:value-of select="$event-class"/>
                                    </type>
                                    
                                    <!-- properties should be carried_out_by or influenced_by -->
                                    <xsl:element name="{$property}">
                                        <_array>
                                            <xsl:apply-templates select="self::node()" mode="production"/>
                                        </_array>
                                    </xsl:element>
                                    
                                    <xsl:if test="mods:role/mods:roleTerm[@authority = 'marcrelator' and @valueURI]">
                                        <technique>
                                            <_array>
                                                <xsl:for-each select="mods:role/mods:roleTerm[@authority = 'marcrelator' and @valueURI]">
                                                    <xsl:variable name="uri" select="@valueURI"/>
                                                    <!-- user Getty AAT URIs when possible, otherwise display MARC relators -->
                                                    <_object>
                                                        <id>
                                                            <xsl:value-of select="
                                                                if ($roles//role[@marcrelator = $uri]/@technique) then
                                                                $roles//role[@marcrelator = $uri]/@technique
                                                                else
                                                                $uri"
                                                            />
                                                        </id>
                                                        <type>Type</type>
                                                        <_label>
                                                            <xsl:value-of select="
                                                                if ($roles//role[@marcrelator = $uri]/@techniqueLabel) then
                                                                $roles//role[@marcrelator = $uri]/@techniqueLabel
                                                                else
                                                                $roles//role[@marcrelator = $uri]"
                                                            />
                                                        </_label>
                                                    </_object>
                                                </xsl:for-each>
                                            </_array>
                                        </technique>
                                    </xsl:if>
                                </_object>
                            </xsl:if>
                        </xsl:for-each>
                    </_array>
                </part>
            </xsl:when>
            <xsl:otherwise>
                <xsl:if test="mods:name">
                    <xsl:variable name="property">
                        <xsl:choose>
                            <xsl:when test="mods:role/mods:roleTerm[@authority = 'marcrelator' and @valueURI]">
                                <xsl:variable name="uri" select="mods:role[1]/mods:roleTerm[@authority = 'marcrelator' and @valueURI][1]/@valueURI"/>
                                
                                <xsl:value-of select="$roles//role[@marcrelator = $uri]/@property"/>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:text>carried_out_by</xsl:text>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:variable>
                    
                    <xsl:if test="not($property = 'provenance')">
                        <xsl:element name="{$property}">
                            <_array>
                                <xsl:apply-templates select="mods:name" mode="production"/>
                            </_array>
                        </xsl:element>
                        
                        <xsl:if test="count(mods:name/mods:role/mods:roleTerm[@authority = 'marcrelator' and @valueURI]) &gt; 0">
                            <technique>
                                <_array>
                                    <xsl:for-each select="distinct-values(mods:name/mods:role/mods:roleTerm[@authority = 'marcrelator']/@valueURI)">
                                        <xsl:variable name="uri" select="."/>
                                        <!-- user Getty AAT URIs when possible, otherwise display MARC relators -->
                                        <_object>
                                            <id>
                                                <xsl:value-of select="
                                                    if ($roles//role[@marcrelator = $uri]/@technique) then
                                                    $roles//role[@marcrelator = $uri]/@technique
                                                    else
                                                    $uri"/>
                                            </id>
                                            <type>Type</type>
                                            <_label>
                                                <xsl:value-of select="
                                                    if ($roles//role[@marcrelator = $uri]/@techniqueLabel) then
                                                    $roles//role[@marcrelator = $uri]/@techniqueLabel
                                                    else
                                                    $roles//role[@marcrelator = $uri]"
                                                />
                                            </_label>
                                        </_object>
                                    </xsl:for-each>
                                </_array>
                            </technique>
                        </xsl:if>
                    </xsl:if>
                </xsl:if>
            </xsl:otherwise>
        </xsl:choose>
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

        <xsl:value-of select="$titleInfo/mods:title"/>
        <xsl:if test="$titleInfo/mods:subTitle">
            <xsl:text>: </xsl:text>
            <xsl:value-of select="$titleInfo/mods:subTitle"/>
        </xsl:if>
    </xsl:function>

</xsl:stylesheet>
