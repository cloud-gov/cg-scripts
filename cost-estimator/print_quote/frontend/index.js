import {
    initializeBlock,
    Button,
    useBase,
    useRecords,
    Box,
    CellRenderer,
    Heading,
    Icon,
    Text,
} from '@airtable/blocks/ui';
import React from 'react';
import printWithoutElementsWithClass from './print_without_elements_with_class';

function PrintInvoice() {
    const base = useBase();

    // We want to render the list of records in this table.
    const table = base.getTableByName('Quotes');

    // At this time, will only work with the 'Current Quote' view
    // of a single quote
    const view = table.getViewByNameIfExists('Current Quote');

    return (
        <div>
            <Toolbar table={table} />
            <Box margin={3}>
                <Report view={view} />
            </Box>
        </div>
    );
}

// The toolbar contains the view picker and print button.
function Toolbar({table}) {
    return (
        <Box className="print-hide" padding={2} borderBottom="thick" display="flex">
            <Button
                onClick={() => {
                    // Inject CSS to hide elements with the "print-hide" class name
                    // when the app gets printed. This lets us hide the toolbar from
                    // the print output.
                    printWithoutElementsWithClass('print-hide');
                }}
                marginLeft={2}
            >
                Print
            </Button>
        </Box>
    );
}

// Renders a <Record> for each of the records in the specified view.
function Report({view}) {
    const records = useRecords(view);

    if (!view) {
        return <div>Pick a view</div>;
    }

    return (
        <div>
            {records.map(record => {
                return( 
            <Box>
                <Heading>Quote ID: {record.name}</Heading>
                <Heading size="small">Date: {record.getCellValueAsString('Date')}</Heading>
                <Heading size="small">For: {record.getCellValueAsString('Agency / Office')}</Heading>
                <CustomerNote record={record}/>
                <CloudLineItems key={record.id} record={record} />
                <CloudSummary record={record} />
                <LaborLineItems key={record.id} record={record} />
            </Box>
                )
            })}
        </div>
    );
}

function CustomerNote({record}) {
    // This rendering of long text does NOT preserve newlines, s
    return (
        <Box>
            <Text>Note to Customer</Text>
            <Box style={{whiteSpace: 'pre-wrap'}} border="default" backgroundColor="white" padding={2} overflow="hidden" >
                <Text marginRight={3}>{record.getCellValueAsString('Note to Customer') ||""}</Text>
            </Box>
        </Box>
    );
}

// Renders a CloudLineItems for the record from the Quotes table 
function CloudLineItems({record}) {
    const base = useBase();

    // Each record in the "Quotes" table will have linked
    // Resource Summaries for which we'll want the Description 
    // and Monthly Credit Cost
    const linkedTable = base.getTableByName('Resource Summaries');
    const linkedRecords = useRecords(
        record.selectLinkedRecordsFromCell('Resource Summaries', {
            // Keep the linked records sorted by their primary field.
            sorts: [{field: linkedTable.primaryField, direction: 'asc'}],
        }),
    );

    return (
        <Box marginY={3}>
            <Heading>Cloud.gov Resource Line Items</Heading>
            <table style={{borderCollapse: 'collapse', width: '100%'}}>
                <thead>
                    <tr>
                        <td style={{width: '50%', verticalAlign: 'bottom'}}>
                            <Heading variant="caps" size="xsmall" marginRight={3} marginBottom={0}>
                                Description
                            </Heading>
                        </td>
                        <td style={{width: '50%', verticalAlign: 'bottom'}}>
                            <Heading variant="caps" size="xsmall" marginRight={3} marginBottom={0}>
                                Monthly Cloud Credits
                            </Heading>
                        </td>
                    </tr>
                </thead>
                <tbody>
                    {linkedRecords.map(linkedRecord => {
                        return (
                            <tr key={linkedRecord.id} style={{borderTop: '2px solid #ddd'}}>
                                <td style={{width: '33%'}}>
                                    <Text marginRight={3}>{linkedRecord.getCellValueAsString('Description') ||"No Description"}</Text>
                                </td>
                                <td style={{width: '50%'}}>
                                    <Text marginRight={3}>{linkedRecord.getCellValueAsString('Monthly Credit Cost') ||"No Cost"}</Text>
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </Box>
    );
}
function CloudSummary({record}) {
    return (
        <Box marginY={3}>
            <table style={{borderCollapse: 'collapse', width: '100%'}}>
                <thead>
                    <tr>
                        <td style={{width: '33%', verticalAlign: 'bottom'}}>
                            <Heading variant="caps" size="xsmall" marginRight={3} marginBottom={0}>
                                Monthly Credit Total
                            </Heading>
                        </td>
                        <td style={{width: '33%', verticalAlign: 'bottom'}}>
                            <Heading variant="caps" size="xsmall" marginRight={3} marginBottom={0}>
                                Credit Tier
                            </Heading>
                        </td>
                        <td style={{width: '33%', verticalAlign: 'bottom'}}>
                            <Heading variant="caps" size="xsmall" marginRight={3} marginBottom={0}>
                                Credits Left in Tier
                            </Heading>
                        </td>
                        <td style={{width: '33%', verticalAlign: 'bottom'}}>
                            <Heading variant="caps" size="xsmall" marginRight={3} marginBottom={0}>
                                Tier Price (Monthly)
                            </Heading>
                        </td>
                    </tr>
                </thead> 
                <tbody>
                    <tr>
                        <td style={{width: '33%', verticalAlign: 'bottom'}}>
                            <Text>144</Text>
                        </td>
                        <td style={{width: '33%', verticalAlign: 'bottom'}}>
                            <Text>Nano</Text>
                        </td>
                        <td style={{width: '33%', verticalAlign: 'bottom'}}>
                            <Text>6</Text>
                        </td>
                        <td style={{width: '33%', verticalAlign: 'bottom'}}>
                            <Text>$7500</Text>
                        </td>
                    </tr>
                </tbody>
            </table>
        </Box>
    );
}

function LaborLineItems({record}) {
    const base = useBase();

    // Each record in the "Quotes" table will have linked
    // Resource Summaries for which we'll want the Description 
    // and Monthly Credit Cost
    const linkedTable = base.getTableByName('Labor Entries');
    const linkedRecords = useRecords(
        record.selectLinkedRecordsFromCell('Labor', {
            // Keep the linked records sorted by their primary field.
            sorts: [{field: linkedTable.primaryField, direction: 'asc'}],
        }),
    );

    return (
        <Box marginY={3}>
            <Heading>Cloud.gov Labor Line Items</Heading>
            <table style={{borderCollapse: 'collapse', width: '100%'}}>
                <thead>
                    <tr>
                        <td style={{verticalAlign: 'bottom'}}>
                            <Heading variant="caps" size="xsmall" marginRight={3} marginBottom={0}>
                                Name
                            </Heading>
                        </td>
                        <td style={{verticalAlign: 'bottom'}}>
                            <Heading variant="caps" size="xsmall" marginRight={3} marginBottom={0}>
                                Description
                            </Heading>
                        </td>
                        <td style={{verticalAlign: 'bottom'}}>
                            <Heading variant="caps" size="xsmall" marginRight={3} marginBottom={0}>
                                Hours
                            </Heading>
                        </td>
                        <td style={{verticalAlign: 'bottom'}}>
                            <Heading variant="caps" size="xsmall" marginRight={3} marginBottom={0}>
                                Labor<br></br>Subtotal
                            </Heading>
                        </td>
                    </tr>
                </thead>
                <tbody>
                    {linkedRecords.map(linkedRecord => {
                        return (
                            <tr key={linkedRecord.id} style={{borderTop: '2px solid #ddd'}}>
                                <td style={{width: '33%'}}>
                                    <Text marginRight={3}>{linkedRecord.getCellValueAsString('Name') ||""}</Text>
                                </td>
                                <td style={{width: '50%'}}>
                                    <Text marginRight={3}>{linkedRecord.getCellValueAsString('Description') ||""}</Text>
                                </td>
                                <td>
                                    <Text marginRight={3}>{linkedRecord.getCellValueAsString('Yearly Hours') ||"0"}</Text>
                                </td>
                                <td>
                                    <Text marginRight={3}>{linkedRecord.getCellValueAsString('Labor Subtotal') ||"0"}</Text>
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </Box>
    );
}
initializeBlock(() => <PrintInvoice />);
