import pytest
from future.backports.datetime import datetime

from dataall.modules.worksheets.api.resolvers import WorksheetRole


@pytest.fixture(scope='module', autouse=True)
def worksheet(client, tenant, group):
    response = client.query(
        """
        mutation CreateWorksheet ($input:NewWorksheetInput){
            createWorksheet(input:$input){
                worksheetUri
                label
                description
                tags
                owner
                userRoleForWorksheet
            }
        }
        """,
        input={
            'label': 'my worksheet',
            'SamlAdminGroupName': group.name,
            'tags': [group.name],
        },
        username='alice',
        groups=[group.name],
        tags=[group.name],
    )
    return response.data.createWorksheet


@pytest.fixture(scope='module', autouse=True)
def mock_s3_client(module_mocker):
    s3_client = module_mocker.patch(
        'dataall.modules.worksheets.services.worksheet_query_result_service.S3Client', autospec=True
    )

    s3_client.return_value.object_exists.return_value = True
    s3_client.return_value.put_object.return_value = None
    s3_client.return_value.get_object.return_value = '123,123,123'
    s3_client.return_value.get_presigned_url.return_value = 'https://s3.amazonaws.com/file/123.csv'
    yield s3_client


def test_create_worksheet(client, worksheet):
    assert worksheet.label == 'my worksheet'
    assert worksheet.owner == 'alice'
    assert worksheet.userRoleForWorksheet == WorksheetRole.Creator.name


def test_list_worksheets_as_creator(client, group):
    response = client.query(
        """
        query ListWorksheets ($filter:WorksheetFilter){
            listWorksheets (filter:$filter){
                count
                page
                pages
                nodes{
                    worksheetUri
                    label
                    description
                    tags
                    owner
                    userRoleForWorksheet
                }
            }
        }
        """,
        filter={'page': 1},
        username='alice',
        groups=[group.name],
    )

    assert response.data.listWorksheets.count == 1


def test_list_worksheets_as_anonymous(client, group):
    response = client.query(
        """
        query ListWorksheets ($filter:WorksheetFilter){
            listWorksheets (filter:$filter){
                count
                page
                pages
                nodes{
                    worksheetUri
                    label
                    description
                    tags
                    owner
                    userRoleForWorksheet
                }
            }
        }
        """,
        filter={'page': 1},
        username='anonymous',
    )

    print(response)
    assert response.data.listWorksheets.count == 0


def test_get_worksheet(client, worksheet, group):
    response = client.query(
        """
            query GetWorksheet($worksheetUri:String!){
                getWorksheet(worksheetUri:$worksheetUri){
                    label
                    description
                    userRoleForWorksheet
                }
            }
        """,
        worksheetUri=worksheet.worksheetUri,
        username='alice',
        groups=[group.name],
    )

    assert response.data.getWorksheet.userRoleForWorksheet == WorksheetRole.Creator.name

    response = client.query(
        """
            query GetWorksheet($worksheetUri:String!){
                getWorksheet(worksheetUri:$worksheetUri){
                    label
                    description
                    userRoleForWorksheet
                }
            }
        """,
        worksheetUri=worksheet.worksheetUri,
        username='anonymous',
    )

    assert 'Unauthorized' in response.errors[0].message


def test_update_worksheet(client, worksheet, group):
    response = client.query(
        """
        mutation UpdateWorksheet($worksheetUri:String!, $input:UpdateWorksheetInput){
            updateWorksheet(
                worksheetUri:$worksheetUri,
                input:$input
            ){
                worksheetUri
                label
            }
        }
        """,
        worksheetUri=worksheet.worksheetUri,
        input={'label': 'change label'},
        username='alice',
        groups=[group.name],
    )

    assert response.data.updateWorksheet.label == 'change label'


def test_create_query_download_url(client, worksheet, env_fixture, group):
    response = client.query(
        """
        mutation CreateWorksheetQueryResultDownloadUrl($input: WorksheetQueryResultDownloadUrlInput){
            createWorksheetQueryResultDownloadUrl(input: $input){
                sqlBody
                AthenaQueryId
                region
                AwsAccountId
                elapsedTimeInMs
                created
                downloadLink
                outputLocation
                expiresIn
                fileFormat
            }
        }
        """,
        input={
            'worksheetUri': worksheet.worksheetUri,
            'athenaQueryId': '123',
            'fileFormat': 'csv',
            'environmentUri': env_fixture.environmentUri,
        },
        username='alice',
        groups=[group.name],
    )

    expires_in = datetime.strptime(response.data.createWorksheetQueryResultDownloadUrl.created, '%Y-%m-%d %H:%M:%S.%f')
    assert response.data.createWorksheetQueryResultDownloadUrl.downloadLink is not None
    assert response.data.createWorksheetQueryResultDownloadUrl.fileFormat == 'csv'
    assert expires_in > datetime.utcnow()


def test_tenant_unauthorized__create_query_download_url(client, worksheet, env_fixture, tenant):
    response = client.query(
        """
        mutation CreateWorksheetQueryResultDownloadUrl($input: WorksheetQueryResultDownloadUrlInput){
            createWorksheetQueryResultDownloadUrl(input: $input){
                sqlBody
                AthenaQueryId
                region
                AwsAccountId
                elapsedTimeInMs
                created
                downloadLink
                outputLocation
                expiresIn
                fileFormat
            }
        }
        """,
        input={
            'worksheetUri': worksheet.worksheetUri,
            'athenaQueryId': '123',
            'fileFormat': 'csv',
            'environmentUri': env_fixture.environmentUri,
        },
    )

    assert response.errors is not None
    assert len(response.errors) > 0
    assert f'is not authorized to perform: MANAGE_WORKSHEETS on {tenant.name}' in response.errors[0].message


def test_resource_unauthorized__create_query_download_url(client, worksheet, env_fixture, group2):
    response = client.query(
        """
        mutation CreateWorksheetQueryResultDownloadUrl($input: WorksheetQueryResultDownloadUrlInput){
            createWorksheetQueryResultDownloadUrl(input: $input){
                sqlBody
                AthenaQueryId
                region
                AwsAccountId
                elapsedTimeInMs
                created
                downloadLink
                outputLocation
                expiresIn
                fileFormat
            }
        }
        """,
        input={
            'worksheetUri': worksheet.worksheetUri,
            'athenaQueryId': '123',
            'fileFormat': 'csv',
            'environmentUri': env_fixture.environmentUri,
        },
        username='bob',
        groups=[group2.name]
    )

    assert response.errors is not None
    assert len(response.errors) > 0
    assert f'is not authorized to perform: DOWNLOAD_ATHENA_QUERY_RESULTS on resource: {worksheet.worksheetUri}' in response.errors[0].message
