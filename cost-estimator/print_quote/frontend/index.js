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
            <Box border="default" backgroundColor="white" padding={2} overflow="hidden" >
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

initializeBlock(() => <PrintInvoice />);
