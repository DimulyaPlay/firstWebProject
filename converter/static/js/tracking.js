import { updatePagination } from './modules/utils.js';

function openPrintWindow(url) {
    const printWindow = window.open(url, '_blank');

    printWindow.onload = function () {
        // Вызываем меню печати после загрузки новой страницы
        printWindow.print();

        // Закрываем вкладку после завершения печати
        printWindow.onafterprint = function () {
            printWindow.close();
        };
    };
}

$(document).ready(function () {
    let currentPage = 1;
    let currentSearchString = '';
    let searchTimeout;


    function updatePostalOrderTable(page, searchString = '') {
        let queryURL = `/api/get-postal-orders?page=${page}&search=${encodeURIComponent(searchString)}`;
        $.ajax({
            url: queryURL,
            type: 'GET',
            dataType: 'json',
            success: function (response) {
                let postalOrders = response.orders;
                let $tbody = $('#postalOrderList');
                let content = '';
                $tbody.empty();
                $tbody.hide();
                if (postalOrders && postalOrders.length > 0) {
                    $.each(postalOrders, function (index, order) {
                        let notificationButton = order.enot_loaded == 1
                            ? `<img data-order-id="${order.id}"src="static/img/enot-image.png" class="enot-print-btn" alt="Извещение" style="cursor: pointer;"></img>`
                            : `<img src="static/img/no-enot-image.png" alt="Извещение отсутствует">`;
                        content += `<tr style="text-align: center;" data-order-id="${order.id}">
                                        <td class="align-middle selectable">${order.sent_date}</td>
                                        <td class="align-middle" style="text-align: left;">${order.comment}</td>
                                        <td class="align-middle">${order.address}</td>
                                        <td class="align-middle">${order.fullName}</td>
                                        <td class="align-middle">${order.last_track}</td>
                                        <td class="align-middle"><img data-order-id="${order.id}" class="moving-print-btn" src="static/img/report-icon.png" alt="Печать" style="cursor: pointer;"></td>
                                        <td class="align-middle">${notificationButton}</td>
                                    </tr>`;
                    });
                } else {
                    $tbody.append('<tr><td colspan="7" class="text-center">Отправлений нет</td></tr>');
                }
                $tbody.append(content);
                $tbody.show();
                updatePagination(response.total_pages, response.current_page, response.start_index_pages, response.end_index_pages);
            },
            error: function (xhr, status, error) {
                console.error("Ошибка загрузки данных: ", error);
            }
        });
    }

    // Обработчик события ввода
    $('#searchString').on('input', function () {
        clearTimeout(searchTimeout); // очищаем предыдущий таймаут
        currentSearchString = $(this).val();

        // Устанавливаем новый таймаут на 1.2 секунды (1200 мс)
        searchTimeout = setTimeout(() => {
            updatePostalOrderTable(1, currentSearchString);
        }, 1200);
    });

    $('tbody').on('click', '.moving-print-btn', function () {
        const orderId = $(this).data('order-id');
        openPrintWindow(`/api/get-tracking?order_id=${orderId}`);
    });

    $('tbody').on('click', '.enot-print-btn', function () {
        const order_id = $(this).data('order-id');
        openPrintWindow(`/api/get-enot?order_id=${order_id}`);
    });

    $('body').on('click', '.page-link', function (e) {
        e.preventDefault();
        currentPage = $(this).data('page');
        updatePostalOrderTable(currentPage, currentSearchString);
    });

    updatePostalOrderTable(currentPage);
});
